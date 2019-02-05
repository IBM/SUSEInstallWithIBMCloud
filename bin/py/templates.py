import StringIO
import ConfigParser

def _getVars(line, varIdentifier="@"):
    lineVars = []
    startIndex = 0

    while startIndex >= 0:
        startIndex= line.find(varIdentifier, startIndex)
        if startIndex >= 0:
            endIndex = line.find(varIdentifier, startIndex+1)
            if endIndex >= 0:
                lineVars.append(line[startIndex+1:endIndex])
                startIndex = endIndex
            startIndex = startIndex+1
    return lineVars if len(lineVars) > 0 else None

class Templates:
    """Class with static methods for handling simple template expansion """

    DEFAULT_IDENTIFIER = "@"

    @staticmethod
    def mergeToFile(template, outFile, vars, extraVars=None, varIdentifier=DEFAULT_IDENTIFIER):
        """
        Merge the template into an output file.

         @type template: str
         @param template: the file name of the template to use

         @type outFile: str
         @param outFile: the file name of the output (expanded) file

         @type vars: dict
         @param vars: the variables to replace in the template

         @type extraVars: dict
         @param extraVars: any values from this dict are "merged" into "vars"
        """
        if outFile is None:
            raise Exception("No out file specified.")
        
        outStream = None
        try:
            with open(outFile, "w") as outStream:
                Templates.mergeToStream(template, outStream, vars, extraVars, varIdentifier)
        finally:
            if outStream:
                outStream.close()

    @staticmethod
    def mergeToString(template, vars, extraVars=None, varIdentifier=DEFAULT_IDENTIFIER):
        """
        Merge the template into a string and return that string.

         @type template: str
         @param template: the template file to use

         @type vars: dict
         @param vars: the variables to replace in the template

         @type extraVars: dict
         @param extraVars: any values from this dict are "merged" into "vars"
        """
        outStrStream = StringIO.StringIO()

        try:
            Templates.mergeToStream(template, outStrStream, vars, extraVars, varIdentifier)
            result = outStrStream.getvalue()
        finally:
            if outStrStream:
                outStrStream.close()
        return result

    @staticmethod
    def mergeToStream(template, outStream, vars, extraVars=None, varIdentifier=DEFAULT_IDENTIFIER):
        """
        Merge the template into provided stream.  
        
        The caller is responsible for:
        - opening the stream and truncating if necessary
        - closing the stream after this function returns

         @type template: str
         @param template: the template file to use

         @type outStream: stream
         @param outStream: the output stream to use

         @type vars: dict
         @param vars: the variables to replace in the template

         @type extraVars: dict
         @param extraVars: any values from this dict are "merged" into "vars"
        """
        if outStream is None:
            raise Exception("No stream provided.")
        elif template is None:
            raise Exception("No template specified")
        varsToUse = vars.copy()
        if extraVars:
            varsToUse.update(extraVars)
    
        fpIn = None
        
        try:
            with open(template, 'r') as fpIn:
                for line in fpIn:
                    outline = line = line.rstrip()
                    lineVars = None
                    lineVars = _getVars(outline, varIdentifier)

                    if lineVars:
                        for var in lineVars:
                            token = "%s%s%s" % (varIdentifier, var, varIdentifier)
                            value = ""
                            if var in varsToUse:
                                valueToUse = varsToUse[var]
                                if isinstance(valueToUse, basestring):
                                    value = valueToUse
                            outline = outline.replace(token,value)
                    outStream.write("%s\n" % outline)
        finally:
            if fpIn:
                fpIn.close()
    
    @staticmethod
    def loadPropertyFile(propFile):
        """
        Load a property file in the form:

          # This is a comment
          PROP1=value1

          # Another comment
          PROP2=value2
        """
        f = None
        
        try:
            with open(propFile) as f:
                config = StringIO.StringIO()
                config.write('[dummy_section]\n')
                config.write(f.read().replace('%', '%%'))
                config.seek(0, os.SEEK_SET)

                cp = ConfigParser.SafeConfigParser()
                cp.readfp(config)

                return dict(cp.items('dummy_section'))
        finally:
            if f:
                f.close()


#############################################################################################
# Main logic here
#############################################################################################
if __name__ == '__main__':
    import argparse
    import os
    import sys

    PROG_ENV_VAR='PROG_NAME'

    def createParser(progName=os.environ[PROG_ENV_VAR] if PROG_ENV_VAR in os.environ else None):
        # create the top-level parser
        parser = argparse.ArgumentParser(progName if progName else None)
        parser.add_argument("-t", "--template", metavar="TEMPLATE_FILE", required=True, help="The template to expand")
        parser.add_argument("-o", "--out", metavar="OUTPUT_FILE", required=True, help="The output file to create")
        parser.add_argument("-i", "--identifier", metavar="VAR_IDENTIFIER", required=False, help="The variable identifier.  The default is the '@' symbol.")
        var_group = parser.add_mutually_exclusive_group(required=True)
        var_group.add_argument("-v", "--var", metavar="VAR=VALUE", nargs="+", action="append")
        var_group.add_argument("-f", "--var-file", metavar="VAR_FILE")

        return parser
    
    def processArgs(args):
        if args.identifier is None:
            args.identifier = Templates.DEFAULT_IDENTIFIER
        
        # if args.template:
        if not os.path.isfile(args.template):
            print("ERROR: cannot find file '%s'" % args.template)
            return 1

        if args.var is None:
            # Then we are going by file
            if not os.path.isfile(args.var_file):
                print("ERROR: cannot find file '%s'" % args.var_file)
                return 1
            try:
                args.var = Templates.loadPropertyFile(args.var_file)
            except Exception as e:
                print("ERROR while loading variables file: %s" % e.message)
                return 2

            print("Expanding template %s using var file: %s" % (args.template, args.var_file))
            args.var_file=None
        else:
            # Then we are going with vars
            vars = { }
            # args.var is a list of an list of string
            for props in args.var:
                for prop in props:
                    try:
                        name, value = prop.split('=', 1)
                        vars[name] = value
                    except:
                        print("ERROR while parsing variable: %s" % prop)
                        return 3
            args.var = vars
            print("Expanding template %s using the specified variables" % args.template)

        try:
            Templates.mergeToFile(args.template, args.out, args.var, varIdentifier=args.identifier)
            print("Output file generated: %s" % args.out)
            return 0
        except Exception as e:
            print("ERROR while expanding template: %s" % e.message)
            return 4
    #
    # Parse args
    #
    parser = createParser()
    args = parser.parse_args()
    print("")
    rc = processArgs(args)
    print("")
    sys.exit(rc)
