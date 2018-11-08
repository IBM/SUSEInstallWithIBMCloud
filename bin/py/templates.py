import StringIO

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

    @staticmethod
    def mergeToFile(template, outFile, vars, extraVars=None, varIdentifier="@"):
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
        
        try:
            with open(outFile, "w") as outStream:
                Templates.mergeToStream(template, outStream, vars, extraVars, varIdentifier)
        finally:
            if outStream:
                outStream.close()

    @staticmethod
    def mergeToString(template, vars, extraVars=None, varIdentifier="@"):
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
    def mergeToStream(template, outStream, vars, extraVars=None, varIdentifier="@"):
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
    
        try:
            with open(template, 'r') as fpIn:
                for line in fpIn:
                    outline = line = line.rstrip()
                    lineVars = None
                    lineVars = _getVars(outline)

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
        except:
            if fpIn:
                fpIn.close()
