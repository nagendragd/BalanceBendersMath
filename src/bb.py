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

class Bounds:
    def __init__(self, difficulty):
        if difficulty == Difficulty.EASY:
            self.max_variables = 3
            self.use_inequality=False
            self.max_coefficient=3
            self.max_constant=10
        if difficulty == Difficulty.MEDIUM:
            self.max_variables = 5
            self.use_inequality=True
            self.max_coefficient=3
            self.max_constant=100
        if difficulty == Difficulty.HARD:
            self.max_variables = 7
            self.use_inequality=True
            self.max_coefficient=3
            self.max_constant=1000
    def allowInequality(self):
        return self.use_inequality
    def getMaxVariables(self):
        return self.max_variables
    def getMaxCoefficient(self):
        return self.max_coefficient
    def getMaxConstant(self):
        return self.max_numeric_constant

class Hint:
    def __init__(self, lhs, op, rhs):
        self.lhs=lhs
        self.op=op
        self.rhs=rhs
        self.fail=False
    def validate(self):
        # make sure the hint is not inconsistent by itself
        # Check 1: at least two different variables appear in equation
        num_var=0
        for item in self.lhs:
            if item != 0:
                num_var+=1
        if num_var < 2:
            for item in self.rhs:
                if item != 0:
                    num_var += 1
        if num_var < 2:
            self.fail=True

        # previous rule did not check that the same variable may have occurred 
        # in both lhs and rhs and effectively would have been just one variable.
        # eg: 2x = 3x
        # Check 2: verify that if only two variable occurrences were counted,
        # then they are not the same variable
        if num_var == 2:
            for idx in len(self.lhs):
                if self.lhs[idx] !=0 and self.rhs[idx]!=0:
                    self.fail=True

        # Check 3: since we do not allow negative numbers (yet),
        # we need variables on either side of the balance.
        if len(self.lhs)==0 or len(self.rhs)==0:
            self.fail=True

        return self.fail

class Question:
    def __init__(self, bounds):
        self.hints=list()
        self.choices=list()
        # first build up a system of linear equations 
        # using the allowed variables and coefficient limits
        # and verify that the system is consistent

    def addHint(self, hint):
        self.hints.append(hint)
    def addChoice(self, choice):
        self.choices.append(choice)
    def validate(self):
        return True

class BB:
    def __init__(self, difficulty, output_name):
        self.difficulty=difficulty
        self.output_name = output_name
        self.questions=list()
        self.assemble()
        self.build()

    def defineNumQuestions(self, difficulty):
        # there's no real rationale for making the
        # number of questions to depend on difficulty level
        # the below is just some initial set up.
        # The way I thought about it: for kids doing EASY
        # we may not want to dump too many questions on them.
        if difficulty == Difficulty.EASY:
            return 4
        if difficulty == Difficulty.MEDIUM:
            return 8
        if difficulty == Difficulty.HARD:
            return 12

    
    def assemble(self):
        info('Assembling questions ...')
        self.num_questions = self.defineNumQuestions(difficulty)
        self.bounds = Bounds(difficulty)
        i=0
        while i<self.num_questions: 
            q=Question(self.bounds)
            if q.validate():
                self.questions.append(q)
                i+=1

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
