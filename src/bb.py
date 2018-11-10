import sys
import os
import random
import numpy as np
from enum import Enum
from reportlab.pdfgen import canvas

#c = canvas.Canvas("hello.pdf")
#c.drawString(100, 750, "Welcome to PDF generation from Python!")
#c.save()

def info(string):
    print ('[INFO]:' + str(string))

def warn(string):
    print ('[WARN]:' + str(string))

def error(string):
    print ('[ERROR]:' + str(string))

def debug(string):
    if debug_flag:
        print('[DEBUG]:'+str(string))

class Difficulty(Enum):
    EASY=1
    MEDIUM=2
    HARD=3

class Bounds:
    def __init__(self, difficulty):
        self.difficulty = difficulty
        if difficulty == Difficulty.EASY:
            self.max_variables = 3
            self.max_variable_value=3
            self.use_inequality=False
            self.max_coefficient=2
            self.max_constant=10
        if difficulty == Difficulty.MEDIUM:
            self.max_variables = 5
            self.max_variable_value=3
            self.use_inequality=False
            self.max_coefficient=3
            self.max_constant=100
        if difficulty == Difficulty.HARD:
            self.max_variables = 7
            self.max_variable_value=3
            self.use_inequality=True
            self.max_coefficient=3
            self.max_constant=1000
    def allowInequality(self):
        return self.use_inequality
    def getMaxVariables(self):
        return self.max_variables
    def getMaxVariableValue(self):
        return self.max_variable_value
    def getMaxCoefficient(self):
        return self.max_coefficient
    def getMaxConstant(self):
        return self.max_numeric_constant

class Hint:
    def __init__(self, vars, lhs, op, rhs):
        self.vars=vars
        self.lhs=lhs
        self.op=op
        self.rhs=rhs
        self.fail=False
    def sameAs(self, hint):
        # we compare the two such that lhs1 == lhs2 or lhs1==rhs2
        # and rhs1=rhs2 or rhs1=lhs2 and op1=op2.
        # we also look for cases where one hint is a reduction of the other.
        # Eg: x+y=z and 2x=2z-2y are the same hint.
        # Our procedure is bring everything over to the LHS 
        # and then to check if they are equal to a scale factor.

        t_us = list()
        for i in range(len(self.lhs)):
            t_us.append(self.lhs[i]-self.rhs[i])
        t_them = list()
        for i in range(len(hint.lhs)):
            t_them.append(hint.lhs[i]-hint.rhs[i])

        # first non-zero denominator determines scale factor
        i=0
        while t_us[i] == 0 and i < len(t_us):
            i+=1
        if i < len(t_us):
            scale_factor=t_them[i]/t_us[i]
            for i in range (len(t_us)):
                if t_us[i]==0 and t_us[i]!=0:
                    return False
                elif t_us[i]!=0:
                    if t_them[i]/t_us[i] != scale_factor:
                        return False

        return True

    def validate(self):
        self.fail=False
        # make sure the hint is not inconsistent by itself
        # Check 0: LHS op RHS is correct
        lhs_sum=0
        for i in range(len(self.lhs)):
            lhs_sum += self.lhs[i]*self.vars[i]
        rhs_sum=0
        for i in range(len(self.rhs)):
            rhs_sum += self.rhs[i]*self.vars[i]
        if self.op == '=':
            if lhs_sum != rhs_sum:
                return False
        if self.op == '<':
            if lhs_sum >= rhs_sum:
                return False
        if self.op == '>':
            if lhs_sum <= rhs_sum:
                return False

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
            for idx in range(len(self.lhs)):
                if self.lhs[idx] !=0 and self.rhs[idx]!=0:
                    self.fail=True

        # Check 3: since we do not allow negative numbers (yet),
        # we need variables on either side of the balance.
        if len(self.lhs)==0 or len(self.rhs)==0:
            self.fail=True

        # Check 4: we need the equation to be non trivial
        # in that -- after simplification -- it should not boil down
        # to a variable becoming equal to 0. For eg:
        # if we had x+y=x, then this will imply y=0.
        # if we had x+2y = 2x+3y, then again this implies x+y=0
        # and this in turn means x=y=0.
        # In order to check for this, we basically move all non-zero
        # coefficients to lhs and see that we have at least two variables
        # with different signs of coefficients.
        t_lhs=list()
        for idx in range(len(self.rhs)):
            t_lhs.append(self.lhs[idx]-self.rhs[idx])

        pve=False
        nve=False
        for idx in range(len(t_lhs)):
            if t_lhs[idx] > 0:
                pve=True
            if t_lhs[idx] < 0:
                nve=True
        if (not pve) or (not nve):
            self.fail=True

        return not self.fail

    def print(self):
        hint_str=''
        for idx in range(len(self.lhs)):
            hint_str+=str(self.lhs[idx]) + ' '
        hint_str+=self.op + ' '
        for idx in range(len(self.rhs)):
            hint_str+=str(self.rhs[idx]) + ' '
        return hint_str

class Question:
    def __init__(self, bounds):
        self.bounds= bounds
        self.hints=list()
        self.choices=list()
        # first build up a system of linear equations 
        # using the allowed variables and coefficient limits
        # and verify that the system is consistent

        # step 1: determine the number of variables 
        num_vars = self.makeNumVars(bounds)
        # First we create some values for the variables
        self.vars=list()
        
        debug('Variable values of the question')
        for j in range (0, num_vars):
            self.vars.append(random.randint(1, bounds.getMaxVariableValue()))
            debug(self.vars[j])

        # for num_vars, how many hints do we need?
        # this would depend on the linear equations we put together of course
        # but for now, assume hints are 1 less than variables
        num_hints = num_vars - 1

        i=0
        while (i<num_hints):
            # make a hint
            # a hint is <LE> <op> <LE> where
            # <LE> is a linear expression and <op> is '=' or '<' or '>'
            # note: we can not have '<=' or '>=' or '!=' since we can not
            # depict this with a balance.
            # Each <LE> can have upto num_vars with coefficients over the bounds

            hint = self.makeHint()

            if hint.validate() and self.uniqueHint(hint):
                if debug_flag:
                    debug(hint.print())

                self.addHint(hint)
                i+=1
    
    def makeHint(self):
        if self.bounds.difficulty == Difficulty.EASY:
            return self.makeHintEasy()
        else:
            return self.makeHintGeneric()

    def makeHintEasy(self):
        # Easy hints are basically one variable each
        num_vars = len(self.vars)
        var1_idx=random.randint(0,num_vars-1)
        var2_idx=random.randint(0,num_vars-1)
        while (var2_idx == var1_idx):
            var2_idx=random.randint(0,num_vars-1)
        # we got two different variables
        # coefficients are assigned as inverse of variable values
        # eg: if variables have values (2 and 3), coefficients are (3 and 2).
        # this ensures balanced equations since easy mode op is always '='
        coeffs_lhs=list()
        coeffs_rhs=list()

        for i in range(num_vars):
            coeffs_lhs.append(0)
            coeffs_rhs.append(0)

        coeffs_lhs[var1_idx]=self.vars[var2_idx]
        coeffs_rhs[var2_idx]=self.vars[var1_idx]
        return Hint(self.vars, coeffs_lhs, '=', coeffs_rhs)
        

    def makeHintGeneric(self):
        coeffs_lhs=list()
        lhs_sum=0
        num_vars = len(self.vars)
        for j in range (0, num_vars):
            coeffs_lhs.append(random.randint(0, self.bounds.getMaxCoefficient()))
            lhs_sum+=coeffs_lhs[j]*self.vars[j]
        if self.bounds.allowInequality():
            op_r = random.randint(0,3)
            if op_r == 0:
                op = '='
            if op_r == 1:
                op = '>'
            if op_r == 2:
                op = '<'
        else:
            op = '='

        rhs_sum=0
        force_z=False
        coeffs_rhs=list()
        for j in range (0, num_vars):
            if not force_z:
                coeffs_rhs.append(random.randint(0, self.bounds.getMaxCoefficient()))
            else:
                coeffs_rhs.append(0)
            rhs_sum += coeffs_rhs[j]*self.vars[j]
            if op == '=' and lhs_sum==rhs_sum:
                # remaining coefficients must all be 0
                force_z=True

        hint = Hint(self.vars, coeffs_lhs, op, coeffs_rhs)
        return hint


    def uniqueHint(self, new_hint):
        for hint in self.hints:
            if new_hint.sameAs(hint):
                return False
        return True

    def makeNumVars(self, bounds):
        nv = bounds.getMaxVariables()
        if nv <= 3:
            return 3
        return random.randint(3, nv)

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
        self.num_questions = self.defineNumQuestions(self.difficulty)
        self.bounds = Bounds(self.difficulty)
        i=0
        while i<self.num_questions: 
            q=Question(self.bounds)
            if q.validate() and self.uniqueQuestions():
                debug('Generated Question ' + str(i))
                self.questions.append(q)
                i+=1

    def build(self):
        info('Building PDF ...')


    def uniqueQuestions(self):
        # verify that we don't have any repeat questions!
        return True
    

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
    debug_flag=True
    args = sys.argv
    mandatory_arg_names = list([('-level', 'Difficulty level (1, 2 or 3)'),('-output', 'Valid Writeable File Path Name of Ooutput PDF File')])
    NUM_MANDATORY_ARGS = 2*len(mandatory_arg_names)
    if len(args) <= NUM_MANDATORY_ARGS:
        error ('Insufficient Arguments')
        usage(mandatory_arg_names)
        sys.exit()
    [difficulty, output_name] = processArgs(args, mandatory_arg_names)
    main(difficulty, output_name)
