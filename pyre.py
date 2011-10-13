#! usr/bin/python
# -*- coding: cp1252 -*-

import ply.lex as lex
import ply.yacc as yacc
import re
import sys

# Lexing

tokens = ('TO', 'FROM', 'WHEN', 'BETWEEN',
          'NUMBER', 'ID', 'STAR', 'QUESTION', 'COMMA', 'PIPE',
          'LPAREN', 'RPAREN', 'LSQUARE', 'RSQUARE', 'LCURLY', 'RCURLY',
          'PLUS', 'MINUS', 'ALPHA', 'NALPHA',
          'EQUALS', 'COLON', 'IMPLIES', 'IMPLIEDBY', 'EQUIV',
          'LPHONEME', 'RPHONEME')
t_ignore = ' \t'
t_TO = r'>'
t_FROM = r'<'
t_WHEN = r'\/'
t_BETWEEN = r'_'
t_ID = r'[a-zA-Z0-9.]+'
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LSQUARE = r'\['
t_RSQUARE = r'\]'
t_LCURLY = r'\{'
t_RCURLY = r'\}'
t_ALPHA = r'@'
t_NALPHA = r'-@'
t_STAR = r'\*'
t_QUESTION = r'\?'
t_COMMA = r','
t_PIPE = r'\|'
t_EQUALS = r'='
t_COLON = r':'
t_IMPLIES = r'=>'
t_IMPLIEDBY = r'<='
t_EQUIV = r'=='
t_LPHONEME = r'`'
t_RPHONEME = r"'"

def t_PLUS(t):
    r'\+'
    t.value = True
    return t

def t_MINUS(t):
    r'-'
    t.value = False
    return t

def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

def t_newline(t):
    r'(\n|\r|\f)+'
    t.lexer.lineno += len(t.value)

def t_error(t):
    """Print an error when an illegal character is found."""
    sys.stderr.write("Warning: Illegal character '%s'\n" % t.value[0])
    t.lexer.skip(1)

lexer = lex.lex(debug=True)

# Phonemes and features

symbols = {}

class Phoneme:
    """
    A wrapper class for a dictionary from features to Booleans.

    A phoneme is a set of signed features. A signed feature is a feature (for
    example, voice) paired with a sign (+ or -). Unspecified features (for
    example, the place of articulation of the Japanese moraic n) are specified
    by their absence from the phoneme.

    The purpose of this wrapper class is to maintain the invariants of
    phonemes, which are specified by constraints.
    """

    def __init__(self, features=dict(), plus=set(), minus=set()):
        """
        Create a new phoneme.

        Optional arguments:
        features : a dictionary from features to Booleans
        plus : a set of positive features
        minus : a set of negative features
        """
        self.features = features.copy()
        self.features.update({f: True for f in plus})
        self.features.update({f: False for f in minus})

    def __repr__(self):
        """
        Return a formal representation of this phoneme as a string.

        Actually, it is not formal.
        """
        return str(self)
    
    def __str__(self):
        """
        Return an informal representation of this phoneme as a string.

        Features are listed in alphabetical order with a '+' or '-' prefix as
        appropriate.
        """
        signed_strings = []
        for key in sorted(self.features.keys()):
            if self[key]: signed_strings.append('+%s' % key)
            else: signed_strings.append('-' + key)
        return '[%s]' % ' '.join(signed_strings)

    def __eq__(self, other):
        """
        Return whether this phoneme's features equal another's.

        Arguments:
        other : the object to test equality against
        """
        if not isinstance(other, Phoneme): return False
        if len(self.features) != len(other.features): return False
        return self <= other

    def __ne__(self, other):
        """
        Return whether this phoneme does not equal an object.

        Arguments:
        other : the object to test inequality against
        """
        return not self == other

    def issubset(self, other):
        """
        Return whether this phoneme is a subset of another.

        A phoneme is a subset of another if every feature of the one appears in
        the other with the same sign.

        Arguments:
        other : the phoneme which might be a superset
        """
        for feature in self.features.keys():
            if feature in other.features:
                if self[feature] != other[feature]:
                    return False
            else:
                return False
        return True

    def __le__(self, other):
        """
        Return whether this phoneme is a subset of an object.

        This is similar to issubset, except that __le__ does not assume that
        the other object is a phoneme.

        Arguments:
        other : the object which might be a subset
        """
        
        return isinstance(other, Phoneme) and self.issubset(other)

    def __hash__(self):
        """Return a hash code for this phoneme."""
        return (hash(tuple(self.features.keys())) ^
                hash(tuple(self.features.values())))

    def contradicts(self, other):
        """
        Return whether this phoneme contradicts another.

        Phonemes contradict each other when any feature of one appears in the
        other with a different sign.

        Arguments:
        other : the phoneme to compare against
        """
        for feature in self.features.keys():
            if feature in other.features and self[feature] != other[feature]:
                return True
        return False

    def contradictsi(self, features):
        """
        Return whether this phoneme contradicts a set of signed features.

        A phoneme contradicts a set of signed features when any feature of the
        phoneme appears in the set with a different sign.

        Arguments:
        features : the dictionary of signed features
        """
        for feature in self.features.keys():
            if feature in features and self[feature] != features[feature]:
                return True
        return False

    def edit(self, other):
        """
        Add another phoneme's signed features, unless any contradict.

        Return this phoneme.

        Arguments:
        other : the phoneme to get the new signed features from
        """
        if self.contradicts(other):
            sys.stderr.write("Warning: Inconsistent feature update\n")
        else:
            self.update(other)
        return self

    def editi(self, features):
        """
        Add some signed features, unless any contradict.

        Return this phoneme.

        Arguments:
        features : the dictionary of signed features
        """
        if self.contradictsi(features):
            sys.stderr.write("Warning: Inconsistent feature update\n")
        else:
            self.updatei(features)
        return self

    def update(self, other):
        """
        Add another phoneme's signed features, overwriting in case of conflict.

        Return this phoneme.

        Arguments:
        other : the phoneme to get the new signed features from
        """
        self.features.update(other.features)
        return self

    def updatei(self, features):
        """
        Add some signed features, overwriting in case of conflict.

        Return this phoneme.

        Arguments:
        features : the dictionary of signed features
        """
        self.features.update(features)
        return self

    def copy(self):
        """Return a copy of this phoneme."""
        return Phoneme(self.features)

    def __getitem__(self, key):
        """
        Return the sign of a feature as a Boolean, or None if it is absent.

        Arguments:
        key : the feature whose sign is wanted
        """
        try:
            return self.features[key]
        except KeyError:
            return None

    def follow_implications(self):
        pass #TODO

def p_error(p):
    """Fail, and go to the next line."""
    sys.stderr.write('Syntax error on line %d on token %s\n' %
                     (p.lexer.lineno, p.type))
    while True:
        tok = yacc.token()
        if not tok: break
    yacc.restart()

def p_line_features(p):
    'line : features_or_new_symbols COLON new_symbols'
    # None : List(Phoneme, Set(String)) Constant Set(String)
    for symbol in p[3]:
        if not symbol in symbols: symbols[symbol] = Phoneme()
        symbols[symbol].edit(p[1][0]) # or update?
        print('%s = %s' % (symbol, symbols[symbol]))

def p_line_new_symbols(p):
    'line : features_or_new_symbols EQUALS features'
    # None : List(Phoneme, Set(String)) Constant Phoneme
    for symbol in p[1][1]:
        if not symbol in symbols: symbols[symbol] = Phoneme()
        symbols[symbol].edit(p[3])
        print('%s = %s' % (symbol, symbols[symbol]))

def p_features_or_new_symbols_base_explicit(p):
    '''
    features_or_new_symbols : PLUS ID
                            | MINUS ID
    '''
    # List(Phoneme, Set(String)) : Boolean String
    p[0] = [Phoneme({p[2]: p[1]}), set([p[1]])]

def p_features_or_new_symbols_base_default(p):
    'features_or_new_symbols : ID'
    # List(Phoneme, Set(String)) : String
    p[0] = [Phoneme({p[1]: True}), set([p[1]])]

def p_features_or_new_symbols_recursive(p):
    'features_or_new_symbols : features_or_new_symbols ID'
    # List(Phoneme, Set(String)) : List(Phoneme, Set(String)) String
    p[1][1].add(p[2])
    p[0] = [p[1][0].updatei({p[2]: True}), p[1][1]]

def p_new_symbols_base(p):
    'new_symbols : ID'
    # Set(String) : String
    p[0] = set([p[1]])

def p_new_symbols_recursive(p):
    'new_symbols : new_symbols ID'
    # List(String) : Set(String) String
    p[1].add(p[2])
    p[0] = p[1]

def p_features_base(p):
    '''
    features : phoneme
             | feature
    '''
    # Phoneme : Phoneme
    p[0] = p[1]

def p_features_recursive(p):
    '''
    features : features phoneme
             | features feature
    '''
    # Phoneme : Phoneme Phoneme
    p[1].update(p[2])
    p[0] = p[1]

def p_feature_explicit(p):
    '''
    feature : PLUS ID
            | MINUS ID
    '''
    # Phoneme : Boolean String
    p[0] = Phoneme({f: p[1] for f in set([p[2]])})

def p_feature_default(p):
    'feature : ID'
    # Phoneme : String
    p[0] = Phoneme({f: True for f in set([p[1]])})

def p_phoneme(p):
    'phoneme : LPHONEME valid_symbol RPHONEME'
    # Phoneme : Constant Phoneme Constant
    p[0] = p[2]

def p_valid_symbol(p):
    'valid_symbol : ID'
    # Phoneme : String
    if not p[1] in symbols:
        sys.stderr.write('Error: No such phoneme %s%s%s\n' %
                         (t_LPHONEME, p[1], t_RPHONEME))
        raise SyntaxError
    p[0] = symbols[p[1]].copy()

# Constraints

constraints = {}

def add_constraint(key, value):
    """
    Add a new key-value pair to the dictionary of constraints.

    A constraint is only added if it is self-consistent, it is not redundant
    with any previous constraints, and it does not contradict any previous
    constraints. If any previous constraint is found to be redundant with it,
    the previous one is replaced.

    Arguments:
    key : the antecedent phoneme
    value : the consequent phoneme
    """
    if not key.contradicts(value):
        worthwhile = True
        for antecedent in constraints.copy():
            consequent = constraints[antecedent]
            #if antecedent <= key and value.contradicts(consequent):
            #   sys.stderr.write('%s <= %s and %s.contradicts(%s)\n' %
            #                    (antecedent, key, value, consequent))
            #   worthwhile = False
            #   break
            if antecedent <= key and value <= consequent:
                print('%s <= %s and %s <= %s' %
                      (antecedent, key, value, consequent))
                worthwhile = False
                break
            if key <= antecedent and consequent <= value:
                print('%s <= %s and %s <= %s' %
                      (key, antecedent, consequent, value))
                del constraints[antecedent]
        if worthwhile:
            if key in constraints: constraints[key].edit(value)
            else: constraints[key] = value

def p_implication(p):
    'line : features_or_new_symbols IMPLIES features'
    # None : List(Phoneme, Set(String)) Constant Phoneme
    add_constraint(p[1][0], p[3])
    print constraints

def p_converse_implication(p):
    'line : features_or_new_symbols IMPLIEDBY features'
    # None : List(Phoneme, Set(String)) Constant Phoneme
    add_constraint(p[3], p[1][0])
    print constraints

# Running the program

parser = yacc.yacc()
while True:
   try:
       s = raw_input('Babel > ')
   except EOFError:
       break
   if not s: continue
   result = parser.parse(s)
   print(result)