import urllib.request
import urllib.parse
import zlib
import time
import re
import xml.dom.pulldom
import argparse
import logging

nDataBytes, nRawBytes, nRecoveries, maxRecoveries = 0, 0, 0, 3


def getData(serverString, command, lexBASE, verbose=1, sleepTime=0):
    global nRecoveries, nDataBytes, nRawBytes
    if sleepTime:
        time.sleep(sleepTime)

    if lexBASE:
        command = urllib.parse.quote(command, safe=lexBASE, encoding=None, errors=None)

    remoteAddr = serverString + '?verb=%s' % command
    
    if verbose:
        logging.info("getData ...'{0}'".format(remoteAddr))

    try:
        with urllib.request.urlopen(remoteAddr) as resp:
            remoteData = str(resp.read().decode('utf-8'))
    except urllib.request.HTTPError as exValue:
        if exValue.code == 503:
            retryWait = int(exValue.hdrs.get("Retry-After", "-1"))
            if retryWait < 0:
                return None
            logging.info("Waiting {:d} seconds".format(retryWait))
            return getData(serverString, command, 0, retryWait)
        logging.warn("http error {0} occured".format(exValue))
        if nRecoveries < maxRecoveries:
            nRecoveries += 1
            return getData(serverString, command, 1, 60)
        return
    
    nRawBytes += len(remoteData)
    
    try:
        remoteData = zlib.decompressobj().decompress(remoteData)
    except:
        pass
    
    nDataBytes += len(remoteData)
    
    mo = re.search('<error *code=\"([^"]*)">(.*)</error>', remoteData)

    eRT = re.search('<ListRecords/>', remoteData)
    
    if mo:
        logging.warn("OAIERROR: code={0} '{1}'".format(mo.group(1), mo.group(2)))
    if eRT and lexBASE:
        logging.info("base repo empty records list")
    else:
        return remoteData

if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s %(levelname)-10s %(message)s", 
        level=logging.INFO,
    )

    parser = argparse.ArgumentParser('pyoaiharvest')

    parser.add_argument(
        "-uri", 
        "--baseURI",  
        help="base URI of the repository",
        required=True,
    )
    parser.add_argument(
        "-o", 
        "--filename", 
        help="write repository to file",
        required=True,
    )
    parser.add_argument(
        "-f", 
        "--from", 
        dest="fromDate",
        help="harvest records from this date yyyy-mm-dd",
    )
    parser.add_argument(
        "-u", 
        "--until", 
        help="harvest records until this date yyyy-mm-dd",
    )
    parser.add_argument(
        "-m", 
        "--mdprefix", 
        default="oai_dc", 
        help="use the specified metadata format prefix",
    )
    parser.add_argument(
        "-s", 
        "--setName",  
        help="harvest the specified set",
    )
    parser.add_argument(
        "--lexBASE", 
        action='store_const',
        const='=()&:+',
        help="base relatet url escaping for '=()&:+'",
    )

    args = parser.parse_args()

    if args:
        serverString = verbOpts = fromDate = untilDate = mdPrefix = oaiSet = lexBASE = ''
        if args.baseURI:
            serverString = args.baseURI
        if args.filename:
            outFileName = args.filename
        if args.fromDate:
            fromDate = args.fromDate
        if args.until:
            untilDate = args.until
        if args.mdprefix:
            mdPrefix = args.mdprefix
        if args.setName:
            oaiSet = args.setName
        if args.lexBASE:    
            lexBASE = args.lexBASE
    else:
        print(usage)

    logging.info("Writing records to {0} from archive {1}".format(
        outFileName,
        serverString,
    ))

    ofile = open(outFileName,"w")

    ofile.write('<repository xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/" \
     xmlns:dc="http://purl.org/dc/elements/1.1/" \
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n')  # wrap list of records with this

    if oaiSet:
        verbOpts += '&set=%s' % oaiSet
    if fromDate:
        verbOpts += '&from=%s' % fromDate
    if untilDate:
        verbOpts += '&until=%s' % untilDate
    if mdPrefix:
        verbOpts += '&metadataPrefix=%s' % mdPrefix

    data = getData(serverString, 'ListRecords' + verbOpts, lexBASE)

    recordCount = 0

    while data:
        events = xml.dom.pulldom.parseString(data)
        for (event, node) in events:
            if event == "START_ELEMENT" and node.tagName == 'record':
                events.expandNode(node)
                node.writexml(ofile)
                recordCount += 1
        mo = re.search('<resumptionToken[^>]*>(.*)</resumptionToken>', data)
        if not mo:
            break
        
        data = getData(serverString, "ListRecords&resumptionToken=%s" % mo.group(1), lexBASE)

    ofile.write('\n</repository>\n'), ofile.close()

    logging.info("Read {:d} bytes ({:.2f} compression)".format(
        nDataBytes,
        (float(nDataBytes)/nRawBytes),
    ))

    logging.info("Wrote out {:d} records".format(recordCount))
