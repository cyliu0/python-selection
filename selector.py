from enum import Enum, auto
from typing import List, Tuple


class Operator(Enum):
    DoesNotExist = "!"
    Equals = "="
    In = "in"
    NotEquals = "!="
    NotIn = "notin"
    Exists = "exists"
    GreaterThan = "gt"
    LessThan = "lt"
    Regex = "re"


class Token(Enum):
    UnknownToken = auto()
    EndOfStringToken = auto()
    IdentifierToken = auto()
    ClosedParToken = auto()
    CommaToken = auto()
    DoesNotExistToken = auto()
    EqualsToken = auto()
    GreaterThanToken = auto()
    InToken = auto()
    LessThanToken = auto()
    NotEqualsToken = auto()
    NotInToken = auto()
    OpenParToken = auto()
    RegexToken = auto()


token_map = {
    ")": Token.ClosedParToken,
    ",": Token.CommaToken,
    "!": Token.DoesNotExistToken,
    "=": Token.EqualsToken,
    ">": Token.GreaterThanToken,
    "in": Token.InToken,
    "<": Token.LessThanToken,
    "!=": Token.NotEqualsToken,
    "notin": Token.NotInToken,
    "(": Token.OpenParToken,
    "re": Token.RegexToken,
}


class Requirement:
    def __init__(self, key: str, operator: str, values: List[str]):
        if operator in (Operator("in"), Operator("notin")):
            if len(values) == 0:
                raise Exception("for 'in', 'notin' operators, values set can't be empty")
        elif operator in (Operator("="), Operator("!="), Operator("re")):
            if len(values) != 1:
                raise Exception("exact-match compatibility requires one single value")
        elif operator in (Operator("exists"), Operator("!")):
            if len(values) != 0:
                raise Exception(f"values: {values} set must be empty for exists and does not exist")
        elif operator in (Operator("gt"), Operator("lt")):
            if len(values) != 1:
                raise Exception("for 'gt', 'lt' operators, exactly one value is required")
            for v in values:
                try:
                    int(v)
                except Exception as e:
                    raise Exception("for 'gt', 'lt' operators, the value must be an integer")
        else:
            raise Exception(f"operator {operator} is not recognized")
        self.key = key
        self.operator = operator
        self.values = values

    def has_value(self, value):
        for v in self.values:
            if v == str(value):
                return True
        return False

    def matches(self, kvs: dict):
        if self.operator in (Operator("in"), Operator("=")):
            if self.key not in kvs:
                return False
            return self.has_value(kvs.get(self.key))
        elif self.operator in (Operator("notin"), Operator("!=")):
            if self.key not in kvs:
                return True
            return not self.has_value(kvs.get(self.key))
        elif self.operator == Operator("exists"):
            return self.key in kvs
        elif self.operator == Operator("!"):
            return self.key not in kvs
        elif self.operator == Operator("re"):
            import re
            return self.key in kvs and re.match(self.values[0], kvs.get(self.key))
        elif self.operator in (Operator("gt"), Operator("lt")):
            if self.key not in kvs:
                return False
            return (self.operator == Operator("gt") and int(kvs.get(self.key)) > int(self.values[0])) or \
                   (self.operator == Operator("lt") and int(kvs.get(self.key)) < int(self.values[0]))
        return False


class Selector:
    def __init__(self, requirements=None):
        if requirements is None:
            requirements = []
        self.requirements = requirements

    def matches(self, kvs):
        for r in self.requirements:
            if not r.matches(kvs):
                return False
        return True


def is_whitespace(char):
    return char in (" ", "\t", "\r", "\n")


def is_special_symbol(char):
    return char in ('=', '!', '(', ')', ',', '>', '<')


class ScannedItem:
    def __init__(self, tok: Token, literal: str):
        self.tok = tok
        self.literal = literal


class Lexer:
    def __init__(self, s: str, pos: int = 0):
        self.s = s
        self.pos = pos

    def read(self):
        b = 0
        if self.pos < len(self.s):
            b = self.s[self.pos]
            self.pos += 1
        return b

    def unread(self):
        self.pos -= 1

    def skip_whitespaces(self, char):
        while True:
            if not is_whitespace(char):
                return char
            char = self.read()

    def scan_id_or_keyword(self):
        buffer = ""
        while True:
            char = self.read()
            if char == 0:
                break
            elif is_special_symbol(char) or is_whitespace(char):
                self.unread()
                break
            else:
                buffer = buffer + char
        if buffer in token_map:
            return token_map[buffer], buffer
        return Token.IdentifierToken, buffer

    def scan_special_symbol(self):
        last_scanned_item = None
        buffer = ""
        while True:
            char = self.read()
            if char == 0:
                break
            elif is_special_symbol(char):
                buffer += char
                if buffer in token_map:
                    last_scanned_item = ScannedItem(tok=token_map[buffer], literal=buffer)
                elif last_scanned_item.tok != Token.UnknownToken:
                    self.unread()
                    break
                else:
                    self.unread()
                    break
            else:
                self.unread()
                break
        if last_scanned_item.tok == Token.UnknownToken:
            return Token.UnknownToken, f"Error expected: keyword found {buffer}"
        return last_scanned_item.tok, last_scanned_item.literal

    def lex(self):
        char = self.skip_whitespaces(self.read())
        if char == 0:
            return Token.EndOfStringToken, ""
        elif is_special_symbol(char):
            self.unread()
            return self.scan_special_symbol()
        self.unread()
        return self.scan_id_or_keyword()


class ParserContext(Enum):
    KeyAndOperator = auto()
    Values = auto()


class Parser:
    def __init__(self, lexer: Lexer, scanned_items=None, position=0):
        if scanned_items is None:
            scanned_items = []
        self.lexer = lexer
        self.scanned_items = scanned_items
        self.position = position

    def lookahead(self, context: ParserContext) -> Tuple[Token, str]:
        tok, lit = self.scanned_items[self.position].tok, self.scanned_items[self.position].literal
        if context == ParserContext.Values:
            if tok in (Token.InToken, Token.NotInToken):
                tok = Token.IdentifierToken
        return tok, lit

    def consume(self, context: ParserContext):
        self.position += 1
        tok, lit = self.scanned_items[self.position - 1].tok, self.scanned_items[self.position - 1].literal
        if context == ParserContext.Values:
            if tok in (Token.InToken, Token.NotInToken):
                tok = Token.IdentifierToken
        return tok, lit

    def scan(self):
        while True:
            token, literal = self.lexer.lex()
            self.scanned_items.append(ScannedItem(tok=token, literal=literal))
            if token == Token.EndOfStringToken:
                break

    def parse_key_and_infer_operator(self):
        operator = None
        tok, literal = self.consume(ParserContext.Values)
        if tok == Token.DoesNotExistToken:
            operator = Operator("!")
            tok, literal = self.consume(ParserContext.Values)
        if tok != Token.IdentifierToken:
            raise Exception(f"found {literal}, expected: identifier")
        t, l = self.lookahead(ParserContext.Values)
        if t in (Token.EndOfStringToken, Token.CommaToken):
            if operator != Operator.DoesNotExist:
                operator = Operator.Exists
        return literal, operator

    def parse_operator(self):
        tok, lit = self.consume(ParserContext.KeyAndOperator)
        if tok == Token.InToken:
            op = Operator.In
        elif tok == Token.EqualsToken:
            op = Operator.Equals
        elif tok == Token.GreaterThanToken:
            op = Operator.GreaterThan
        elif tok == Token.LessThanToken:
            op = Operator.LessThan
        elif tok == Token.NotInToken:
            op = Operator.NotIn
        elif tok == Token.NotEqualsToken:
            op = Operator.NotEquals
        elif tok == Token.RegexToken:
            op = Operator.Regex
        else:
            raise Exception(f"found '{lit}', expected: '=', '!=', '==', 'in', 'notin'")
        return op

    def parse_values(self):
        tok, lit = self.consume(ParserContext.Values)
        if tok != Token.OpenParToken:
            raise Exception(f"found '{lit}', expected: '('")
        tok, lit = self.lookahead(ParserContext.Values)
        if tok in (Token.IdentifierToken, Token.CommaToken):
            s = self.parse_identifiers_list()
            tok, lit = self.consume(ParserContext.Values)
            if tok != Token.ClosedParToken:
                raise Exception(f"found '{lit}', expected: ')'")
            return s
        elif tok == Token.ClosedParToken:
            self.consume(ParserContext.Values)
            return StringSet("")
        raise Exception(f"found '{lit}', expected: ',', ')'")

    def parse_identifiers_list(self):
        s = StringSet()
        while True:
            tok, lit = self.consume(ParserContext.Values)
            if tok == Token.IdentifierToken:
                s.insert(lit)
                tok2, lit2 = self.lookahead(ParserContext.Values)
                if tok2 == Token.CommaToken:
                    s.insert("")
                elif tok2 == Token.ClosedParToken:
                    return s
                else:
                    raise Exception(f"found '{lit2}', expected: ',' or ')'")
            elif tok == Token.CommaToken:
                tok2, lit2 = self.lookahead(ParserContext.Values)
                if tok2 == Token.ClosedParToken:
                    s.insert("")
                    return s
                if tok2 == Token.CommaToken:
                    self.consume(ParserContext.Values)
                    s.insert("")
            else:
                return s

    def parse_exact_values(self):
        s = StringSet()
        tok, lit = self.lookahead(ParserContext.Values)
        if tok in (Token.EndOfStringToken, Token.CommaToken):
            s.insert("")
            return s
        tok, lit = self.consume(ParserContext.Values)
        if tok == Token.IdentifierToken:
            s.insert(lit)
            return s
        raise Exception(f"found '{lit}', expected: identifier")

    def parse_requirement(self):
        key, operator = self.parse_key_and_infer_operator()
        if operator in (Operator.Exists, Operator.DoesNotExist):
            return Requirement(key, operator, [])
        operator = self.parse_operator()
        values = StringSet()
        if operator in (Operator.In, Operator.NotIn):
            values = self.parse_values()
        elif operator in (Operator.Equals, Operator.NotEquals, Operator.GreaterThan, Operator.LessThan, Operator.Regex):
            values = self.parse_exact_values()
        return Requirement(key, operator, values.list())

    def parse(self):
        self.scan()
        requirements = []
        while True:
            tok, lit = self.lookahead(ParserContext.Values)
            if tok in (Token.IdentifierToken, Token.DoesNotExistToken):
                r = self.parse_requirement()
                requirements.append(r)
                t, l = self.consume(ParserContext.Values)
                if t == Token.EndOfStringToken:
                    return requirements
                elif t == Token.CommaToken:
                    t2, l2 = self.lookahead(ParserContext.Values)
                    if t2 not in (Token.IdentifierToken, Token.DoesNotExistToken):
                        raise Exception(f"found '{l2}', expected: identifier after ','")
                else:
                    raise Exception(f"found '{l}', expected: ',' or 'end of string'")
            elif tok == Token.EndOfStringToken:
                return requirements
            else:
                raise Exception(f"found '{lit}', expected: !, identifier, or 'end of string'")


class StringSet:
    def __init__(self, *items):
        self.set = {}
        self.insert(*items)

    def insert(self, *items):
        for item in items:
            self.set[item] = True

    def list(self):
        return list(self.set.keys())


def parse(selector: str):
    p = Parser(Lexer(selector))
    items = p.parse()
    items.sort(key=lambda x: x.key)
    return Selector(items)
