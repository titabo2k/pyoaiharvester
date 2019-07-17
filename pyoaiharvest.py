import urllib.request
import urllib.parse
import zlib
import time
import argparse
import logging
from lxml import etree

nDataBytes, nRawBytes, nRecoveries, maxRecoveries = 0, 0, 0, 3

nameSpaces = {
    'oai': 'http://www.openarchives.org/OAI/2.0/',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
}

xpaths = {                                                                                                                                    
    'res_token_xpath': '//oai:resumptionToken', 
    'oai_error_code_xpath': '//oai:error/@code',
    'oai_error_val_xpath': '//oai:error[@code="{}"]',
    'record_xpath': '//oai:record',                                                                                            
}

def parseData(remoteAddr, remoteData, nameSpaces, xpaths):
    doc = etree.XML(remoteData)

    oaiErrorCode = ''
    oaiErrorVal = ''
    
    try:
        oaiErrorCode = doc.xpath(
            xpaths['oai_error_code_xpath'],
            namespaces=nameSpaces)[0]
    except IndexError as noOAIErrorCode:
        pass
    
    if oaiErrorCode:
        oai_error_val_xpath = xpaths['oai_error_val_xpath'].format(
            oaiErrorCode,
        )

        try:
            oaiErrorVal = doc.xpath(
                oai_error_val_xpath,
                namespaces=nameSpaces)[0].text
        except IndexError as noOAIErrorVal:
            pass

        logging.fatal("oai error {0}: {1}".format(
            oaiErrorCode,
            oaiErrorVal,
        ))

        raise Exception("oai error {0}: {1}".format(
            oaiErrorCode,
            oaiErrorVal,
        ))

    records = ''
    resToken = ''

    if not oaiErrorCode:
        try:
            records = doc.xpath(
                xpaths['record_xpath'],
                namespaces=nameSpaces)
        except IndexError as noRecords:
            pass

        try:
            resToken = doc.xpath(
                xpaths['res_token_xpath'], 
                namespaces=nameSpaces)[0].text
        except IndexError as noResToken:
            logging.info("no resumption token found for {0}".format(
                remoteAddr))
            pass

    if records or resToken:
        return records, resToken


def getData(serverString, command, lexBASE, verbose=1, sleepTime=0):
    global nRecoveries, nDataBytes, nRawBytes
    if sleepTime:
        time.sleep(sleepTime)

    if lexBASE:
        command = urllib.parse.quote(
            command, 
            safe=lexBASE, 
            encoding=None, 
            errors=None,
        )

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

    records, resToken = parseData(remoteAddr, remoteData, nameSpaces, xpaths)

    return records, resToken


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

    ofile.write('<repository>\n')  # wrap list of records with this

    if oaiSet:
        verbOpts += '&set=%s' % oaiSet
    if fromDate:
        verbOpts += '&from=%s' % fromDate
    if untilDate:
        verbOpts += '&until=%s' % untilDate
    if mdPrefix:
        verbOpts += '&metadataPrefix=%s' % mdPrefix

    hasToken = True
    curResToken = ''
    recordCount = 0

    while hasToken:
        resToken = ''
        records = ''
        if curResToken:
            try:
                records, resToken = getData(
                    serverString, 
                    "ListRecords&resumptionToken=%s" % curResToken, 
                    lexBASE)
            except TypeError:
                hasToken = False
                pass
            curResToken = resToken
        else:
            try:
                records, resToken = getData(serverString, 'ListRecords' + verbOpts, lexBASE)
            except TypeError:
                hasToken = False
                pass
            curResToken = resToken

        for rec in records:
            ofile.write(etree.tostring(rec, encoding='unicode'))
            recordCount += 1

    ofile.write('</repository>\n'), ofile.close()

    logging.info("Read {:d} bytes ({:.2f} compression)".format(
        nDataBytes,
        (float(nDataBytes)/nRawBytes),
    ))

    logging.info("Wrote out {:d} records".format(recordCount))
