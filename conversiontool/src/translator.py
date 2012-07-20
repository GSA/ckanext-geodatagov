import os
import sys
import datetime
import urlparse
import urllib
import cgi
import tempfile
import java.lang.System as System
import java.lang.Class as Class
import java.io.File as JavaFile
import java.io.StringReader as StringReader
import javax.xml.transform.TransformerConfigurationException as \
    TransformerConfigurationException
import java.sql.DriverManager as DriverManager
import java.sql.SQLException as SQLException
import javax.xml.transform.Transformer as Transformer
import javax.xml.transform.TransformerFactory as TransformerFactory
import javax.xml.transform.TransformerException as TransformerException
import javax.xml.transform.stream.StreamResult as StreamResult
import javax.xml.transform.stream.StreamSource as StreamSource
import com.ziclix.python.sql.zxJDBC as zxJDBC

import logging
logging.basicConfig(filename='errors.log',
                    format='%(asctime)s\n%(message)s',
                    level=logging.ERROR)


def usage():
    ''' Usage info '''
    print """
    jython src/translator.py <username> <password> <connstring> <path-to-xslt>

    <username> - The username for connecting to the DB
    <password> - The password for the user above
    <connstring> - The connection string to connect to
    <path-to-xslt> - Path to the XSLT to use
    """
    return 1


_transform = None
_errors = 0
_count = 0
_batch = 100
_write_connection = None


def transform(xlst, xmldoc, docuuid):
    '''
    Runs the transform from the specified xslt against the provided
    document.  The transformer is only loaded on the first run and
    then kept in memory for re-use.
    '''
    global _transform
    global _errors
    global _count

    if _transform is None:
        tFactory = TransformerFactory.newInstance()
        try:
            _transform = tFactory.newTransformer(StreamSource(JavaFile(xslt)))
        except TransformerConfigurationException, tce:
            print tce
            print '*' * 70
            print 'This is likely that your license file for saxon is '\
                  'missing or that there is a genuine error in the XSLT'
            sys.exit(1)

    _count = _count + 1
    if _count % 1000 == 0:
        System.gc()

    fid, path, = tempfile.mkstemp()
    os.close(fid)

    try:
        print '\r + Processing document %s' % (docuuid,),
        _transform.transform(StreamSource(StringReader(xmldoc)),
                             StreamResult(JavaFile(path)))

        f = open(path)
        store_document_result(f.read(), docuuid)
        f.close()
        os.remove(path)
    except TransformerException, e:
        _errors = _errors + 1
        msg = "Error: %s\nFile:  %s\nDoc UUID: %s\n" % (e, resultfile, docuuid)
        store_document_result("", docuuid, msg)
        logging.error(msg)


def get_document_count(connection):
    '''
    Counts how many records are available for us to process
    '''
    query = """
        select count(D.*) from "GPT_RESOURCE" R
               join "GPT_COLLECTION_MEMBER" M using("DOCUUID")
               join "GPT_RESOURCE_DATA" D using("DOCUUID")
               where "SITEUUID" is null;
    """.strip()
    stmt = connection.createStatement()
    rs = stmt.executeQuery(query)

    rs.next()
    count = rs.getInt(1)

    rs.close()
    stmt.close()

    return count


def get_documents(connection, offset=0):
    '''
    Queries to get a resultset containing all of the XML documents that we
    want to process. The resultset can be retrieved an item at a time.

    TODO: We should constrain this to ones that we haven't processed in the
          last X hours for the actual solution
    '''
    global _batch

    query = '''select D.* from "GPT_RESOURCE" R
               join "GPT_COLLECTION_MEMBER" M using("DOCUUID")
               join "GPT_RESOURCE_DATA" D using("DOCUUID")
               where "SITEUUID" is null  LIMIT %d OFFSET %d;'''.strip() % \
        (_batch, offset,)

    stmt = connection.createStatement()
    rs = stmt.executeQuery(query)
    return stmt, rs


def store_document_result(doc, docuuid, error=None):
    '''
    Stores the result of the transformation back into the database
    for later retrieval
    '''
    stmt = _write_connection.createStatement()
    stmt.executeUpdate("delete from xslt_results where uuid='%s'" % docuuid)
    stmt.close()

    ps = _write_connection.prepareStatement(
        "INSERT INTO xslt_results VALUES (?, ?, ?)")
    ps.setString(1, docuuid)
    ps.setString(2, doc)
    ps.setString(3, error or '')
    ps.executeUpdate()
    ps.close()


def get_connection(jdbc_url, driverName):
    """
        Given the name of a JDBC driver class and the url to be used
        to connect to a database, attempt to obtain a connection to
        the database.
    """
    try:
        Class.forName(driverName).newInstance()
    except Exception, msg:
        print msg
        sys.exit(-1)

    try:
        dbConn = DriverManager.getConnection(jdbc_url)
    except SQLException, msg:
        print msg
        sys.exit(-1)

    return dbConn


def run_conversion(username, password, connstring, xslt):
    '''
    Runs the conversion of XML files from the specified database and
    using the provided XSLT.
    '''
    global _batch
    global _write_connection

    resultdir = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                             '../data/output/'))

    # Before we connect to the remote DB we should check that we can actually
    # load the XSLT file.
    if not os.path.exists(xslt):
        print "Can't find the XSLT file"
        sys.exit(1)

    url_parts = list(urlparse.urlparse(connstring))
    url_parts[4] = urllib.urlencode({'user': username, 'password': password})
    connstring = urlparse.urlunparse(url_parts)

    try:
        connection = get_connection(connstring, 'org.postgresql.Driver')
        _write_connection = get_connection(connstring, 'org.postgresql.Driver')
    except zxJDBC.DatabaseError, e:
        print e
        sys.exit(1)

    offset = 0
    count = get_document_count(connection)

    run_total = int(os.getenv("RUNTOTAL") or count)

    while offset < run_total:
        stmt, results = get_documents(connection, offset)

        # While we keep pulling back results, we should keep processing
        # them, taking care to allow the transform function to log any
        # particular errors it encounters.
        while results.next():
            identifier = results.getString(1)
            xmldoc = results.getString(3)
            transform(xslt, xmldoc, identifier)

        results.close()
        stmt.close()
        offset += _batch

    _write_connection.close()
    connection.close()


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(usage())

    start = datetime.datetime.now()
    System.setProperty("javax.xml.transform.TransformerFactory",
                       "net.sf.saxon.TransformerFactoryImpl")

    _, username, password, connstring, xslt, = sys.argv
    run_conversion(username, password, connstring, xslt)

    end = datetime.datetime.now()
    print "\nRun completed %d documents in %s with %d errors" % (_count,
                                                                 end - start,
                                                                 _errors)
    if _errors:
        print "Please check errors.log for information on failures"
