#!/usr/bin/python

import os
import re
import sys

file_list = []

if len(sys.argv) <= 2 or (sys.argv[1] != 'on' and sys.argv[1] != 'off'):
    print "Specify 'on' or 'off' then the files..."
    print "'on' will add function debug statements"
    print "'off' will remove all debug statements"
    sys.exit(1)

TYPE_OF_RUN = sys.argv[1]

for i in range( 2, len(sys.argv) ):
    file_list.append( sys.argv[i] )
    
class_regex = re.compile( '^\s*?class (.*)[(]?.*?[)]?:' )
function_regex = re.compile( '^(\s*?)def (.*)[(]?.*?[)]?:' )
debug_regex = re.compile( 'DEBUG' )

SIZE_OF_SPACING = ' ' * 4
    
for file in file_list:

    in_file = None
    out_file = None

    try:
        in_file = open( file, 'r' )
        out_file = open( file + '.tmp', 'w' )
        files_opened_properly = True

    except IOError:
        print file + ' was not found...'
        files_opened_properly = False

    if files_opened_properly:
    
        if TYPE_OF_RUN == 'on':
    
            class_name = ""
            old_function_spacing = None
        
            for line in in_file:
                
                out_file.write(line)
    
                function_spacing = ""
                function_name = ""
    
                function_match = function_regex.search(line)
                
                if function_match != None:
                
                    function_spacing, function_name = function_match.group(1), function_match.group(2)
    
                    if old_function_spacing == None:
                        old_function_spacing = function_spacing                    
                    
                    # if we are now on a different indent spacing length then assume we have left the
                    # class
                    if old_function_spacing != function_spacing:
                        class_name = ""
                    
                    if class_name != "":
                        out_file.write( function_spacing + SIZE_OF_SPACING + 'print "DEBUG: (' + file + ') ' + class_name + '.' + function_name + '"\n' )
                    else:
                        out_file.write( function_spacing + SIZE_OF_SPACING + 'print "DEBUG: (' + file + ') ' + function_name + '"\n' )
                
                else:
                    class_match = class_regex.match(line)
                    
                    if class_match != None:
                        class_name = class_match.group(1)
                        
        else:
            for line in in_file:
                if debug_regex.search( line ) == None:
                    out_file.write(line)
        
    if in_file != None:
        in_file.close()
        
    if out_file != None:
        out_file.close()

    if files_opened_properly:
        os.system( 'mv ' + file + '.tmp' + ' ' + file )
