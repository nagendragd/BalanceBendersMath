import sys
import os
import random
import math
import numpy as np
from pathlib import Path
from enum import Enum
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import letter, landscape

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


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
            self.max_variables = 6
            self.max_variable_value=4
            self.use_inequality=False
            self.max_coefficient=2
            self.max_constant=10
            self.num_choices=4
        if difficulty == Difficulty.MEDIUM:
            self.max_variables = 6
            self.max_variable_value=4
            self.use_inequality=False
            self.max_coefficient=3
            self.max_constant=100
            self.num_choices=4
        if difficulty == Difficulty.HARD:
            self.max_variables = 7
            self.max_variable_value=3
            self.use_inequality=True
            self.max_coefficient=3
            self.max_constant=1000
            self.num_choices=6
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
        self.correct_choice=False
        self.vars=list()
        self.lhs=list()
        self.rhs=list()
        for i in range(len(vars)):
            self.vars.append(vars[i])
            self.lhs.append(lhs[i])
            self.rhs.append(rhs[i])
        self.op=op
        self.fail=False
    def getLHSCoeffTotal(self):
        t=0
        for i in self.lhs:
            t+=i
        return t
    def getRHSCoeffTotal(self):
        t=0
        for i in self.rhs:
            t+=i
        return t

    def identical(self, h):
        for i in range(len(self.lhs)):
            if self.lhs[i] != h.lhs[i]:
                return False
        for i in range(len(self.rhs)):
            if self.rhs[i] != h.rhs[i]:
                return False

        return True

    def sameAs(self, hint):
        # we compare the two such that lhs1 == lhs2 or lhs1==rhs2
        # and rhs1=rhs2 or rhs1=lhs2 and op1=op2.
        # we also look for cases where one hint is a reduction of the other.
        # Eg: x+y=z and 2x=2z-2y are the same hint.
        # Our procedure is bring everything over to the LHS 
        # and then to check if they are equal to a scale factor.

        # first silly check: the num variables are the same in both
        if len(self.lhs) != len(hint.lhs):
            return False

        t_us = list()
        for i in range(len(self.lhs)):
            t_us.append(self.lhs[i]-self.rhs[i])
        t_them = list()
        for i in range(len(hint.lhs)):
            t_them.append(hint.lhs[i]-hint.rhs[i])

        # first non-zero denominator determines scale factor
        i=0
        while (i < len(t_us)) and (t_us[i] == 0): 
            i+=1
        if i < len(t_us):
            scale_factor=t_them[i]/t_us[i]
            for j in range (0, len(t_us)):
                if t_us[j]==0 and t_them[j]!=0:
                    return False
                elif t_us[j]!=0:
                    if t_them[j]/t_us[j] != scale_factor:
                        return False

        return True

    def validateChoice(self):
        self.fail=False

        # Check 1: at least two different variables appear in equation
        num_lhs=0
        for item in self.lhs:
            if item != 0:
                num_lhs+=1
        num_rhs=0
        for item in self.rhs:
            if item != 0:
                num_rhs += 1
        if num_lhs == 0 or num_rhs == 0:
            self.fail=True

        # previous rule did not check that the same variable may have occurred 
        # in both lhs and rhs and effectively would have been just one variable.
        # eg: 2x = 3x
        # Check 2: verify that if only two variable occurrences were counted,
        # then they are not the same variable
        if num_lhs + num_rhs == 2:
            for idx in range(len(self.lhs)):
                if self.lhs[idx] !=0 and self.rhs[idx]!=0:
                    self.fail=True

        return not self.fail

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

        # Check 1: we need the equation to be non trivial
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
            return False

        res = self.validateChoice()
        self.fail = not res

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
        self.num_choices = bounds.num_choices
        self.choices=list()
        # first build up a system of linear equations 
        # using the allowed variables and coefficient limits
        # and verify that the system is consistent

        # step 1: determine the number of variables 
        self.num_vars = self.makeNumVars(bounds)
        # First we create some values for the variables
        self.vars=list()
        
        debug('Variable values of the question')
        for j in range (0, self.num_vars):
            self.vars.append(random.randint(1, bounds.getMaxVariableValue()))
            debug('v'+str(j) + ': ' + str(self.vars[j]))

        # we discovered one bug wherein some of the answer choices
        # used variables that had not been displayed in hints.
        # this was basically unsolvable!
        # now we add a data structure to keep track of which variables
        # have actually showed up on one or more hints.
        # Our answer choices should not use any other variables
        self.used_vars=list()
        for j in range (0, self.num_vars):
            self.used_vars.append(False)

        # for num_vars, how many hints do we need?
        # this would depend on the linear equations we put together of course
        # but for now, assume hints are 1 less than variables
        num_hints = self.num_vars - 1

        i=0
        while (i<num_hints):
            # make a hint
            # a hint is <LE> <op> <LE> where
            # <LE> is a linear expression and <op> is '=' or '<' or '>'
            # note: we can not have '<=' or '>=' or '!=' since we can not
            # depict this with a balance.
            # Each <LE> can have upto num_vars with coefficients over the bounds

            t_hints = self.makeHints()

            for j in range(len(t_hints)):
                # pick a random hint from the generated set
                if len(t_hints) > 1:
                    idx = random.randint(0, len(t_hints)-1)
                else:
                    idx = 0
                chosen_hint = t_hints[idx]
                if chosen_hint.validate() and self.isUnique(self.hints, chosen_hint):
                    if debug_flag:
                        debug(chosen_hint.print())

                    self.addHint(chosen_hint)
                    i+=1
                    break

        # now that we have constructed our hints,
        # we add choices of which one or more may be correct!
        # The only rules we have are:
        # 1. no hint should repeat as a choice!
        # 2. no two choices must be the same!
        # 3. at least one choice should be correct!
        debug('Printing Choices..')
        correct_star=''
        nc=0
        if self.num_choices == 4:
            need_num_correct = 1
        else:
            need_num_correct = 2
        found_num_correct=0
        while (nc < self.num_choices): 
            add_choice=False
            if (nc==self.num_choices-need_num_correct) and (found_num_correct < need_num_correct):
                choices = self.makeHints()
                if len(choices):
                    choice = choices[0]
            else:
                choice = self.makeChoice()
            if choice.validateChoice() and self.isUnique(self.choices, choice) and not self.isIdentical(self.hints, choice):
                if choice.validate():
                    correct_star='*'
                    found_this_correct=True
                    choice.correct_choice = True
                else:
                    correct_star=''
                    found_this_correct=False
                if nc >= self.num_choices-need_num_correct:
                    if found_this_correct:
                        self.choices.append(choice)
                        if debug_flag:
                            debug(correct_star+choice.print())
                        found_num_correct += 1
                        nc+=1
                else:
                    self.choices.append(choice)
                    if debug_flag:
                        debug(correct_star+choice.print())
                    nc+=1

    def makeChoiceGeneric(self):
        return self.makeChoiceEasy()

    def makeChoiceEasy(self):
        # Easy choices are basically one variable each
        num_vars = len(self.vars)
        var1_idx=random.randint(0,num_vars-1)
        var2_idx=random.randint(0,num_vars-1)
        while (var2_idx == var1_idx):
            var2_idx=random.randint(0,num_vars-1)
        coeffs_lhs=list()
        coeffs_rhs=list()

        for i in range(num_vars):
            coeffs_lhs.append(0)
            coeffs_rhs.append(0)

        coeffs_lhs[var1_idx]=random.randint(1, self.bounds.getMaxCoefficient())
        coeffs_rhs[var2_idx]=random.randint(1, self.bounds.getMaxCoefficient())
        return Hint(self.vars, coeffs_lhs, '=', coeffs_rhs)

    def sameAs(self, q):
        # Two questions are the same if they have the same hints.
        # If at least one hint is different, then the questions
        # are different.

        # first we check if the two questions have the same number of variables
        # if not, they are different.
        if len(self.hints[0].lhs) != len(q.hints[0].lhs):
            return False
        for h in self.hints:
            matched_hint=False
            for t_h in q.hints:
                if h.sameAs(t_h):
                    matched_hint=True
            if matched_hint == False:
                return False
        return True

    def makeChoice(self):
        if self.bounds.difficulty == Difficulty.EASY:
            return self.makeChoiceEasy()
        elif self.bounds.difficulty == Difficulty.MEDIUM:
            return self.makeChoiceEasy()
        else:
            return self.makeChoiceGeneric()
    
    def makeHints(self):
        hint_list=list()
        if self.bounds.difficulty == Difficulty.EASY:
            hint_list.append(self.makeHintEasy())
        elif self.bounds.difficulty == Difficulty.MEDIUM:
            return self.makeHintsMedium()
        else:
            hint_list.append(self.makeHintGeneric())
        return hint_list

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

        add_equal_extra = random.randint(0,2)
        add_just_one = random.randint(0,2)
        if add_equal_extra==1:
            for i in range(num_vars):
                if coeffs_rhs[i] == 0 and coeffs_lhs[i] == 0:
                    coeffs_rhs[i] = coeffs_lhs[i] = random.randint(1,self.bounds.getMaxCoefficient())
                    if add_just_one == 1:
                        break
        return Hint(self.vars, coeffs_lhs, '=', coeffs_rhs)
        
    def makeHintsMedium(self):
        hint_list = list()
        num_vars = len(self.vars)
        coeffs_lhs=list()
        coeffs_rhs=list()

        for i in range(num_vars):
            coeffs_lhs.append(0)
            coeffs_rhs.append(0)

        # search the space of coefficients to determine equalities
        # of the kind: x + 3w = 2y + 2z for example

        # we favor smaller equations over larger ones

        num_solutions = 0
        try_lhs_num_vars = 2
        num_tried=0
        while num_solutions < 2:
            num_tried += 1
            if num_tried > 128:
                if try_lhs_num_vars < num_vars:
                    try_lhs_num_vars += 1
                    num_tried = 1
            for i in range(num_vars):
                coeffs_rhs[i]=0
            try_nz=0
            for i in range (num_vars):
                if try_nz < try_lhs_num_vars:
                    coeffs_lhs[i] = random.randint(0,self.bounds.getMaxCoefficient())
                else:
                    coeffs_lhs[i] = 0
                if coeffs_lhs[i] != 0:
                    try_nz += 1

            # see if we can match this on the RHS side
            valid_rhs_found = True
            update_coeff_idx=num_vars - 1
            while valid_rhs_found:
                if coeffs_rhs[update_coeff_idx] < self.bounds.getMaxCoefficient():
                    coeffs_rhs[update_coeff_idx] += 1
                else:
                    valid_rhs_found = False
                    while (update_coeff_idx > -1) and (not valid_rhs_found):
                        if coeffs_rhs[update_coeff_idx] == self.bounds.getMaxCoefficient():
                            update_coeff_idx -= 1
                        else:
                            # we can increase this coefficient by one
                            coeffs_rhs[update_coeff_idx] += 1
                            # reset all coeffs to the "right" back to 0
                            for i in range (update_coeff_idx+1, num_vars):
                                coeffs_rhs[i] = 0
                            update_coeff_idx = num_vars - 1
                            valid_rhs_found = True
                if valid_rhs_found:
                    # see if this satisfies: lhs Op rhs
                    l_sum = 0
                    r_sum = 0
                    for idx in range (len(coeffs_lhs)):
                        l_sum += coeffs_lhs[idx] * self.vars[idx]
                    for idx in range (len(coeffs_rhs)):
                        r_sum += coeffs_rhs[idx] * self.vars[idx]
                    if l_sum == r_sum:
                        hint = Hint(self.vars, coeffs_lhs, '=', coeffs_rhs)
                        hint_list.append(hint)
                        num_solutions += 1
                else:
                    # no solution found
                    break
                
        return hint_list
        

    def makeHintGeneric(self):
        # We have the variable values with us.
        # We need to get a set of coefficient values to create
        # balanced equations that satisfy lhs op rhs.
        #

        coeffs_lhs=list()
        lhs_sum=0
        num_vars = len(self.vars)
        for j in range (0, num_vars):
            coeffs_lhs.append(random.randint(0, self.bounds.getMaxCoefficient()))
            lhs_sum+=coeffs_lhs[j]*self.vars[j]
        if self.bounds.allowInequality():
            op_r = random.randint(0,3)
            if op_r == 0:
                op = '<'
            elif op_r == 1:
                op = '>'
            else:
                op = '='
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


    def isUnique(self, hint_list, new_hint):
        for hint in hint_list:
            if new_hint.sameAs(hint):
                return False
        return True

    def isIdentical(self, hint_list, new_hint):
        for hint in hint_list:
            if new_hint.identical(hint):
                return True
        return False

    def makeNumVars(self, bounds):
        nv = bounds.getMaxVariables()
        if nv <= 3:
            return 3
        return random.randint(3, nv)

    def addHint(self, hint):
        self.hints.append(hint)
        # we also update our tracker of which variables
        # have appeared amongst our hints
        for j in range (0, len(hint.lhs)):
            if hint.lhs[j]>0 or hint.rhs[j]>0:
                self.used_vars[j] = True

    def addChoice(self, choice):
        self.choices.append(choice)
    def validate(self):
        # check that all variables have been covered
        for i in range (0, self.num_vars):
            if self.used_vars[i] == False:
                return False
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
            return 6
        if difficulty == Difficulty.HARD:
            return 10

    
    def assemble(self):
        info('Assembling questions ...')
        self.num_questions = self.defineNumQuestions(self.difficulty)
        self.bounds = Bounds(self.difficulty)
        i=0
        while i<self.num_questions: 
            q=Question(self.bounds)
            if q.validate() and self.isUniqueQuestion(q):
                debug('Generated Question ' + str(i))
                self.questions.append(q)
                i+=1


    def build(self):
        info('Building PDF ...')
        self.page_idx=-1

        #bal = "../images/balance2.jpg"
        #im = Image(bal, 5.5*inch, 0.75*inch)
        #c_shape = "../images/circle.jpg"
        #cir = Image(c_shape, 0.4*inch, 0.4*inch)
        #s_shape = "../images/square.jpg"
        #squ = Image(s_shape, 0.4*inch, 0.4*inch)
        #p_shape = "../images/pentagon.jpg"
        #pen = Image(p_shape, 0.4*inch, 0.4*inch)
#
#        c = canvas.Canvas("hello.pdf", pagesize=letter)
#        c.setFont('Helvetica', 14)
#        c.drawString(100, 800, 'This is so Cool!')
#        # left side of the scale
#        im.drawOn(c, 100, 650)
#        cir.drawOn(c,130, 704)
#        squ.drawOn(c,170, 704)
#        pen.drawOn(c,210, 704)
#        cir.drawOn(c,130, 733)
#        squ.drawOn(c,170, 733)
#        pen.drawOn(c,199, 733)

#        # right side of the scale
#        cir.drawOn(c,320, 704)
#        squ.drawOn(c,349, 704)
#        pen.drawOn(c,465, 704)
#        cir.drawOn(c,330, 733)
#        squ.drawOn(c,370, 733)
#        pen.drawOn(c,399, 733)
#        c.save()

        if Path(self.output_name).exists():
            warn('File: ' + self.output_name + ' already exists')
            if os.access(self.output_name, os.W_OK)==False:
                error('File: ' + self.output_name + ' can not be written to!')
                sys.exit()
        else:
            # check if directory is writeable
            dir_name = os.path.dirname(self.output_name)
            if dir_name is None or dir_name=='':
                dir_name='.'
            if Path(dir_name).exists==False:
                error ('Invalid directory path: ' + dir_name)
                sys.exit()
            if os.access(dir_name, os.W_OK) == False:
                error('Directory: ' + dir_name +  ' can not be written to!')
                sys.exit()

        # Now we should be ok to write to the output.
        c = canvas.Canvas(self.output_name, pagesize=letter)
        c.setFont('Helvetica', 14)
        self.pageInit()
        t = 'Enjoy your puzzles! (Difficulty level: ' + self.toDifficultyStr(self.difficulty) + ')' 

        self.writeText2PDF(c, t)

        for i in range (0, self.num_questions):
            self.writeQuestionToPDF(c, self.questions[i], i+1)

        c.showPage()
        self.writeText2PDF(c, 'Answer key:')
        for i in range (0, self.num_questions):
            s = 'Q'+str(i+1)+': '
            for j in range (0, len(self.questions[i].displayed_choices)):
                choice = self.questions[i].displayed_choices[j]
                if choice.correct_choice:
                    s += str(j+1) + ', '
            self.writeText2PDF(c, s)

        c.showPage()
        c.save()

    def writeQuestionToPDF(self, canv, q, q_id):
        # A question comprises a header, hints and choices
        # we first decide if there's enough space in the page
        # to display all of it, if not, we output current page,
        # and start a new page for the question.

        # assign shapes to coefficients
        self.assignShapeImages(q.num_vars)

        use_extra_page = False
        total_height=self.text_height 
        for hint in q.hints:
            total_height += self.hint_height + self.spacing
        total_height += self.text_height + self.spacing
        for choice in q.choices:
            total_height += self.choice_height + self.spacing
        if total_height > self.page_height - self.bottom_margin:
            use_extra_page = True
            warn ('Question does not fit on a single page!')
            warn ('Choices will be displayed on the page after the puzzle hints page.')

        self.writeText2PDF(canv, 'Puzzle ' + str(q_id))
        for hint in q.hints:
            self.writeHint(canv, hint)
            if self.y < (self.hint_height + self.bottom_margin):
                canv.showPage()
                self.pageInit()
        #if use_extra_page: 
        #    canv.showPage()
        #    self.pageInit()

        self.x=self.left_margin
        self.writeText2PDF(canv, 'Circle the correct choices')

        c_idx=0

        # first we randomize the order in which
        # we write our choices. This is done as our
        # algorithm to generate choices ends up generally making the
        # last choice as the correct choice. This would be a give away
        # if we presented them this way for every question.
        t_choices = self.randomizeChoices(q.choices)

        q.displayed_choices = t_choices
        for choice in t_choices:
            self.writeText2PDFRaw(canv, self.x, self.y - self.choice_height/2, '('+str(c_idx+1)+')')
            self.y -= self.choice_height 
            self.x += self.choice_number_width
            self.writeChoice(canv, choice)
            self.y -= self.spacing
            self.x = self.left_margin

            if self.y <= (self.choice_height + self.bottom_margin):
                canv.showPage()
                self.pageInit()

            c_idx += 1

        canv.showPage()
        self.pageInit()
        q.displayed_choices = t_choices
    def randomizeChoices(self, choices):
        n_c = len(choices)
        rand_offset = random.randint(1, n_c)
        out_choices=list()
        for idx in range (0, n_c):
            out_choices.append(choices[(idx+rand_offset) % n_c])
        return out_choices


    def writeHint(self, canv, hint):
        bal = "../images/balance2.jpg"
        im = Image(bal, 5.5*inch, 0.75*inch)
        self.x = self.left_margin
        y=self.y
        im.drawOn(canv, self.x, self.y-self.hint_height)

        # now place the non-zero coeff shapes on the scales
        self.placeShapes(canv, hint.lhs)
        self.x = self.right_scale_x
        self.placeShapes(canv, hint.rhs)

        self.y = y - self.hint_height
        self.y -= self.spacing

    def scaleHeight(self):
        return self.scale_height

    def placeShapes(self, canv, coeffs):
        num_shapes=0
        for coeff in coeffs:
            num_shapes += coeff

        num_rows = math.ceil(num_shapes/self.max_shapes_per_scale_row)

        x=self.x
        y=self.y - self.hint_height + self.scaleHeight()
        if num_rows == 1:
            idx=0
            total_x_space_for_shapes = num_shapes*self.shape_width
            inter_shape_x_space = int((self.scale_width - total_x_space_for_shapes)/(num_shapes+1))
            for coeff in coeffs:
                if coeff > 0:
                    for j in range (0, coeff):
                        x += inter_shape_x_space
                        self.shapes[idx].drawOn(canv, x, y)
                        x += self.shape_width
                        
                idx += 1
        else:
            # we stack each shape vertically.
            # ie, all instances of a shape go vertically up.
            num_nz_vars=0
            for coeff in coeffs:
                if coeff > 0:
                    num_nz_vars+=1
            total_x_space_for_shapes = num_nz_vars*self.shape_width
            inter_shape_x_space = int((self.scale_width - total_x_space_for_shapes)/(num_nz_vars+1))
            idx=0
            for coeff in coeffs:
                if coeff > 0:
                    x += inter_shape_x_space
                    y=self.y - self.hint_height + self.scaleHeight()
                    for j in range (0, coeff):
                        # stack them up vertically
                        self.shapes[idx].drawOn(canv, x, y)
                        y += self.shape_height
                    x += self.shape_width

                idx+=1


    def assignShapeImages(self, num_vars):
        self.shapes=list()
        self.equals_shape=Image("../images/equals.jpg", 0.4*inch, 0.4*inch)
        rand_offset = random.randint(0, self.max_shapes)
        for idx in range (0, num_vars):
            r_idx = (idx + rand_offset) % self.max_shapes
            if r_idx == 0:
                image = "../images/circle.jpg"
            elif r_idx == 1:
                image = "../images/pentagon.jpg"
            elif r_idx == 2:
                image = "../images/triangle.jpg"
            elif r_idx == 3:
                image = "../images/hexagon.jpg"
            elif r_idx == 4:
                image = "../images/square.jpg"
            elif r_idx == 5:
                image = "../images/diamond.jpg"
            else:
                error('Unsupported index: No shape available')
                image = None
            shape = Image(image, 0.4*inch, 0.4*inch)
            self.shapes.append(shape)

    def writeChoice(self, canv, choice):
        var_idx=0
        for coeff in choice.lhs:
            if coeff != 0:
                for i in range (0, coeff):
                    self.shapes[var_idx].drawOn(canv, self.x, self.y)
                    self.x += self.shape_width + self.shape_x_gap
            var_idx+=1

        if choice.op == '=':
            self.equals_shape.drawOn(canv, self.x, self.y)
            self.x += self.shape_width + self.shape_x_gap

        var_idx=0
        first_right_shape_x = self.x
        for coeff in choice.rhs:
            if coeff != 0:
                for i in range (0, coeff):
                    self.shapes[var_idx].drawOn(canv, self.x, self.y)
                    self.x += self.shape_width + self.shape_x_gap
                    if self.x >= self.page_width - self.right_margin:
                        # need a new row to write the rest of the shapes
                        self.y -= (self.shape_height + self.spacing)
                        self.x  = first_right_shape_x
            var_idx+=1


    def pageInit(self):
        self.page_idx+=1
        self.page_width = letter[0]
        self.page_height = letter[1]
        self.text_height=15
        self.left_margin = 50
        self.top_margin = 30
        self.bottom_margin = 20
        self.spacing = 5
        self.hint_height=150
        self.choice_height=35
        self.choice_number_width=30
        self.shape_width=29
        self.shape_height=29
        self.shape_x_gap=5
        self.scale_width=174
        self.scale_height=54
        self.right_scale_x=273
        self.right_margin = self.shape_width
        self.max_shapes = 6 # TBD: must be done dynamically by counting shapes in the images/ folder
        self.max_shapes_per_scale_row=int(self.scale_width/self.shape_width)
        
        self.x=self.left_margin
        self.y=self.page_height-self.top_margin

    def writeText2PDF(self, canv, text):
        if not self.y >= self.bottom_margin + self.text_height:
            canv.showPage()
            self.pageInit()
        canv.drawString(self.x, self.y, text)
        self.y -= (self.text_height + self.spacing)

    def writeText2PDFRaw(self, canv, x, y, text):
        canv.drawString(x, y, text)

    def toDifficultyStr(self, level):
        if level == Difficulty.EASY:
            return 'Easy'
        elif level == Difficulty.MEDIUM:
            return 'Medium'
        elif level == Difficulty.HARD:
            return 'Hard'
        else:
            return 'Unknown'


    def isUniqueQuestion(self, q):
        # verify that we don't have any repeat questions!
        # However rare this may be, we simply can not allow this.
        # Unless we want to be left red-faced when a kid calls up
        # and says she got a set of duplicate puzzles!
        for ques in self.questions:
            if ques.sameAs(q):
                return False

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
                warn('File with the given name already exists. Will be overwritten..')
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
