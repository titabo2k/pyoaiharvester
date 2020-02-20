import urllib.request
import urllib.parse
import zlib
import time
import argparse
import logging
import gzip
from lxml import etree
import http.client

nDataBytes, nRawBytes, nRecoveries, maxRecoveries, recoveryWait = 0, 0, 0, 30, 60

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

def provideFileHandle(targetDir, fileNum, outFileName):
    fullPath = "{0}/{1}_{2}".format(targetDir, fileNum, outFileName)

    outFile = None

    if gzipedOut:
        outFile = gzip.open(fullPath,"wt")
    else:
        outFile = open(fullPath,"w")

    return outFile


def parseData(remoteAddr, remoteData, nameSpaces, xpaths):
    remoteData = bytes(bytearray(remoteData, encoding='utf-8'))

    parser = None
    doc = None
    
    try:
        parser = etree.XMLParser(ns_clean=True)
        doc = etree.XML(remoteData, parser=parser)
    except etree.XMLSyntaxError as em:
        logging.warn(("first attempt to parse the by {addr} provided xml failed, " + 
            "error was:\n{error}\ndata was:\n{data}").format(
                addr=remoteAddr,
                error=em,
                data=remoteData))
        try:
            parser = etree.XMLParser(ns_clean=True, recover=True)
            doc = etree.XML(remoteData, parser=parser)
        except etree.XMLSyntaxError as em:
            logging.fatal(("failed to parse the by {addr} provided xml, " + 
            "error was:\n{error}\ndata was:\n{data}").format(
                addr=remoteAddr,
                error=em,
                data=remoteData))
            raise em

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
    global nRecoveries, nDataBytes, nRawBytes, recoveryWait
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
    except (urllib.request.HTTPError, http.client.RemoteDisconnected) as exValue:
        if exValue.code == 503:
            retryWait = int(exValue.hdrs.get("Retry-After", "-1"))
            if retryWait < 0:
                return None
            logging.info("Waiting {:d} seconds".format(retryWait))
            return getData(serverString, command, 0, retryWait)
        logging.warn("http error {0} occured".format(exValue))
        if nRecoveries < maxRecoveries:
            nRecoveries += 1
            logging.info("try {} of {} retries, waiting for {} sec".format(
                nRecoveries, maxRecoveries, recoveryWait))
            return getData(serverString, command, 1, recoveryWait)
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
        "-dir", 
        "--targetDir", 
        help="target dir",
        required=True,
    )
    parser.add_argument(
        "-fn", 
        "--fileBaseName", 
        help="base name of the target files",
        required=True,
    )
    parser.add_argument(
        "-max", 
        "--maxRecNum", 
        type=int,
        default=10000, 
        help="max num of records per file",
    )
    parser.add_argument(
        "-rn", 
        "--rootNode", 
        default="root", 
        help="root node to wrap the harvested oai records",
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
    parser.add_argument(
        "-gz",
        "--gzipedOut",
        action='store_true',
        help="provide gziped file as output",
    )

    args = parser.parse_args()

    serverString = args.baseURI
    targetDir = args.targetDir
    outFileName = args.fileBaseName
    maxRecNum = args.maxRecNum
    rootNode = args.rootNode
    fromDate = args.fromDate
    untilDate = args.until
    mdPrefix = args.mdprefix
    oaiSet = args.setName
    lexBASE = args.lexBASE
    gzipedOut = args.gzipedOut

    verbOpts = ''

    if oaiSet:
        verbOpts += '&set=%s' % oaiSet
    if fromDate:
        verbOpts += '&from=%s' % fromDate
    if untilDate:
        verbOpts += '&until=%s' % untilDate
    if mdPrefix:
        verbOpts += '&metadataPrefix=%s' % mdPrefix

    if maxRecNum == 0:
        maxRecNum += 1

    if gzipedOut:
        outFileName += ".gz"

    hasToken = True
    curResToken = ''
    recordCount = 0
    fileNum = 0
    curFileRecNum = 0

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

        if (records and (curFileRecNum == 0)):
            ofile = provideFileHandle(targetDir, fileNum, outFileName)
            ofile.write("<{}>\n".format(rootNode))

        for rec in records:
            if curFileRecNum == maxRecNum:
                ofile.write("</{}>".format(rootNode))
                ofile.close()
                
                logging.info("wrote {:d} records to {}/{:d}_{}".format(
                curFileRecNum,
                targetDir,
                fileNum,
                outFileName,
                ))
                
                curFileRecNum = 0
                fileNum += 1
                
                ofile = provideFileHandle(targetDir, fileNum, outFileName)
                ofile.write("<{}>\n".format(rootNode))

            ofile.write(etree.tostring(rec, encoding='unicode'))
            recordCount += 1
            curFileRecNum += 1

    ofile.write("</{}>".format(rootNode))
    ofile.close()

    logging.info("wrote {:d} records to {}/{:d}_{}".format(
        curFileRecNum,
        targetDir,
        fileNum,
        outFileName,
    ))

    logging.info("Read {:d} bytes ({:.2f} compression)".format(
        nDataBytes,
        (float(nDataBytes)/nRawBytes),
    ))

    logging.info("wrote out {:d} records".format(recordCount))
