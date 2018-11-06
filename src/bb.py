import sys
import os
from enum import Enum
from reportlab.pdfgen import canvas

#c = canvas.Canvas("hello.pdf")
#c.drawString(100, 750, "Welcome to PDF generation from Python!")
#c.save()

def info(string):
    print ('[INFO]:' + string)

def warn(string):
    print ('[WARN]:' + string)

def error(string):
    print ('[ERROR]:' + string)

class Difficulty(Enum):
    EASY=1
    MEDIUM=2
    HARD=3

class BB:
    def __init__(self, difficulty, output_name):
        self.difficulty=difficulty
        self.output_name = output_name
        self.assemble()
        self.build()
    
    def assemble(self):
        info('Assembling questions ...')

    def build(self):
        info('Building PDF ...')
    

def main(difficulty_level, output_name):
    BB(difficulty_level, output_name)

def usage(mandatory_arg_names):
    info ('Program takes ' + str(len(mandatory_arg_names)) + ' arguments')
    for name in mandatory_arg_names:
        info('Argument name:'+'\"'+name[0]+'\"'+' with value: ' + name[1])

def processArgs(args, mandatory_arg_names):
    idx=1
    difficulty=None
    output_name=None
    while idx < len(args):
        arg = args[idx]
        if arg.lower() == '-level':
            if args[idx+1]=='1':
                difficulty=Difficulty.EASY
            elif args[idx+1]=='2':
                difficulty=Difficulty.MEDIUM
            elif args[idx+1]=='3':
                difficulty=Difficulty.HARD
            else:
                warn('Difficulty level: ' + args[idx+1] + ' is not valid. Use 1, 2 or 3.')
                difficulty=Difficulty.MEDIUM
            idx+=2
        elif arg.lower() == '-output':
            # verify that path exists, and is writeable
            output_name = args[idx+1]
            dir_name = os.path.dirname(output_name)
            if dir_name == '':
                dir_name = '.'
            if os.path.exists(dir_name)==False:
                error('Directory path not found: ' + dir_name)
                sys.exit()
            if os.path.exists(output_name) == True:
                error('File with the given name already exists. Please specify a different name')
                sys.exit()
            if os.access(dir_name, os.W_OK) == False:
                error('File path not writeable: ' + dir_name)
                sys.exit()
            idx+=2
        else:
            warn('Unknown argument: ' + args[idx] + ' ignored')
            idx+=1
    return [difficulty, output_name]

if __name__ == '__main__':
    args = sys.argv
    mandatory_arg_names = list([('-level', 'Difficulty level (1, 2 or 3)'),('-output', 'Valid Writeable File Path Name of Ooutput PDF File')])
    NUM_MANDATORY_ARGS = 2*len(mandatory_arg_names)
    if len(args) <= NUM_MANDATORY_ARGS:
        error ('Insufficient Arguments')
        usage(mandatory_arg_names)
        sys.exit()
    [difficulty, output_name] = processArgs(args, mandatory_arg_names)
    main(difficulty, output_name)
