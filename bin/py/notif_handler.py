#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
from os import curdir, sep
from urlparse import urlparse
import cgi
import threading
import sys, traceback

from utils import restartDHCP
from dhcp_conf_helper import DhcpConfEntry, DhcpConfHelper

# This class will handles any incoming requests comming from the bare metals installing SUSE
class NotificationHandler(BaseHTTPRequestHandler):
    _dhcpConfFilename = '/etc/dhcp/dhcpd.conf'
    _server = None

    @classmethod
    def setServer(cls, server):
        cls._server = server

    @classmethod
    def setDhcpConfFilename(cls, filename):
        cls._dhcpConfFilename = filename
    
    def shutdownHandler(self):
        stopServerThread = threading.Thread(target=self._server.shutdown)
        stopServerThread.daemon = True
        stopServerThread.start()

    def returnPage(self,text):
        self.send_response(200)
        self.send_header('Content-type','text/html')
        self.end_headers()
        # Send the html message
        self.wfile.write(text)
        return
    def returnAckJson(self):
        self.send_response(200)
        self.send_header('Content-type','application/json')
        self.end_headers()
        # Send the html message
        self.wfile.write('{"status":"success"}')
        return


    #Handler for the GET requests
    def do_GET(self):
        try:
            if self.path.startswith("/installationCompleted"):
                if self.path == "/installationCompleted" or self.path == "/installationCompleted?":
                    print( "Expected params")
                elif self.path.startswith("/installationCompleted?"):
                    if self.path.count('?') > 0:
                        query = urlparse(self.path).query
                        try:
                            params = dict(qc.split("=") for qc in query.split("&"))
                            print("")
                            if 'hostname' in params:
                                hostname = params['hostname']
                                
                                print("Received notification from '%s' that first stage of OS installation completed.  " % hostname)
                                self.handleInstallationCompleted(hostname)
                        except:
                            print( "Failed parsing the parameters: %s" % self.path)
                            traceback.print_exc(file=sys.stdout)
                            self.send_error(500, "Unexpected error occurred")
                else:
                    self.send_error(400, "Invalid parameter")
            elif self.path.startswith("/shutdown"):
                self.returnAckJson()
                self.shutdownHandler()
            else:
                self.send_error(404,'File Not Found: %s' % self.path)
        except IOError:
            self.send_error(500,'Unexpected error for path: %s' % self.path)

    # Handler for the POST requests
    def do_POST(self):
        self.send_error(405,'POST not supported: %s' % self.path)
        return            

    def handleInstallationCompleted(self, hostname):
        dhcpConf = DhcpConfHelper(self._dhcpConfFilename)
        dhcpGroup = dhcpConf.getGroup()
        success = False

        try:
            if dhcpGroup.removeChild(DhcpConfEntry.Type.Host, hostname):
                print("DHCP configuration for host '%s' removed." % hostname)
                if dhcpConf.save():
                    print("\nChanges saved in %s\n" % dhcpConf.getFilename())
                    restartDHCP()
            else:
                print("DHCP configuration for host '%s' not found." % hostname)
            success = True
            print("Processed notification from '%s' successfully" % hostname)
            self.returnAckJson()
        except:
            print("Failure to handle event from: %s" % hostname)
            traceback.print_exc(file=sys.stdout)
            self.send_error(400, "Invalid parameter")

        # Check if there are any more server to wait for.
        serversList = dhcpGroup.getChildren(DhcpConfEntry.Type.Host)

        # Check if there are any servers left to wait for.
        if serversList is None or len(serversList) == 0:
            print("No more hosts to wait for.  Stopping the listener.")
            self.shutdownHandler()

        # Return the status of the processing
        return success
                               
    
# server = None

# try:
#     # Create the server and define the handler to manage the incomming requests
#     server = HTTPServer(('', bootServerListenPort), NotificationHandler)
#     print 'Started httpserver on port ' , bootServerListenPort
    
#     # Wait forever for incoming http requests
#     server.serve_forever()

# except KeyboardInterrupt:
#     print '^C received, shutting down the web server'
#     server.socket.close()
