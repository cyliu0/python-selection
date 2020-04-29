from unittest import TestCase
from selector import Parser, Lexer, Token, ParserContext, parse


class TestLexer(TestCase):
    def test_lex(self):
        cases = [
            ("", Token.EndOfStringToken),
            (",", Token.CommaToken),
            ("notin", Token.NotInToken),
            ("in", Token.InToken),
            ("=", Token.EqualsToken),
            (">", Token.GreaterThanToken),
            ("<", Token.LessThanToken),
            ("!", Token.DoesNotExistToken),
            ("!=", Token.NotEqualsToken),
            ("(", Token.OpenParToken),
            (")", Token.ClosedParToken),
            ("re", Token.RegexToken),
        ]
        for c in cases:
            l = Lexer(c[0], 0)
            token, lit = l.lex()
            assert token == c[1], f"found '{token}', want '{c[1]}'"
            assert lit == c[0], f"found '{lit}', want: '{c[0]}'"


class TestParser(TestCase):
    def test_scan(self):
        cases = [
            ("key in ( value )", 6)
        ]
        for c in cases:
            sel = c[0]
            length = c[1]
            p = Parser(Lexer(sel, 0))
            p.scan()
            assert length == len(
                p.scanned_items), f"length not matched, scanned items: {len(p.scanned_items)}, want: {length}, selector: '{sel}'"

    def test_lookahead(self):
        cases = [
            ("key in ( value )",
             [Token.IdentifierToken, Token.InToken, Token.OpenParToken, Token.IdentifierToken, Token.ClosedParToken,
              Token.EndOfStringToken]),
            ("key notin ( value )",
             [Token.IdentifierToken, Token.NotInToken, Token.OpenParToken, Token.IdentifierToken, Token.ClosedParToken,
              Token.EndOfStringToken]),
            ("key in ( value1, value2 )",
             [Token.IdentifierToken, Token.InToken, Token.OpenParToken, Token.IdentifierToken, Token.CommaToken,
              Token.IdentifierToken, Token.ClosedParToken, Token.EndOfStringToken]),
            ("key", [Token.IdentifierToken, Token.EndOfStringToken]),
            ("!key", [Token.DoesNotExistToken, Token.IdentifierToken, Token.EndOfStringToken]),
            ("()", [Token.OpenParToken, Token.ClosedParToken, Token.EndOfStringToken]),
            ("", [Token.EndOfStringToken]),
            ("x in (),y",
             [Token.IdentifierToken, Token.InToken, Token.OpenParToken, Token.ClosedParToken, Token.CommaToken,
              Token.IdentifierToken, Token.EndOfStringToken]),
            ("!= (), = notin",
             [Token.NotEqualsToken, Token.OpenParToken, Token.ClosedParToken, Token.CommaToken, Token.EqualsToken,
              Token.NotInToken, Token.EndOfStringToken]),
            ("key>2", [Token.IdentifierToken, Token.GreaterThanToken, Token.IdentifierToken, Token.EndOfStringToken]),
            ("key<1", [Token.IdentifierToken, Token.LessThanToken, Token.IdentifierToken, Token.EndOfStringToken])
        ]
        for c in cases:
            p = Parser(Lexer(c[0], 0))
            p.scan()
            while True:
                token, lit = p.lookahead(ParserContext.KeyAndOperator)
                token2, lit2 = p.consume(ParserContext.KeyAndOperator)
                if token == Token.EndOfStringToken:
                    break
                assert token == token2, f"token not matched, token: '{token}', token2: '{token2}'"
                assert lit == lit2, f"literal not matched, lit: '{lit}', lit2: '{lit2}'"


class TestSelector(TestCase):
    def test_parse(self):
        cases = [
            ("", 0),
            ("x=y", 1)
        ]
        for c in cases:
            sel = c[0]
            length = c[1]
            p = parse(sel)
            assert len(p.requirements) == length, f"expected requirements: {len(p.requirements)}, want: {length}"

    def test_matches(self):
        cases = [
            ("", {"x": "y"}, True),
            ("x=y", {"x": "y"}, True),
            ("x=y,z=w", {"x": "y", "z": "w"}, True),
            ("x!=y,z!=w", {"x": "z", "z": "a"}, True),
            ("notin=in", {"notin": "in"}, True),
            ("x", {"x": "z"}, True),
            ("!x", {"y": "z"}, True),
            ("x>1", {"x": "2"}, True),
            ("x<1", {"x": "0"}, True),
            ("x re ^dog", {"x": "doggy"}, True),
            ("x in (a, b)", {"x": "b"}, True),
            ("x notin (a, b)", {"x": "c"}, True),
            ("x=z", {}, False),
            ("x=z", {"x": "y"}, False),
            ("x=z,y=w", {"x": "w", "y": "w"}, False),
            ("x!=z,y!=w", {"x": "z", "y": "w"}, False),
            ("x", {"y": "z"}, False),
            ("!x", {"x": "z"}, False),
            ("x>1", {"x": "0"}, False),
            ("x<1", {"x": "2"}, False),
            ("x re ^dog", {"x": "dooggy"}, False),
            ("x in (a, b)", {"x": "c"}, False),
            ("x notin (a, b)", {"x": "b"}, False),
        ]
        for c in cases:
            sel = c[0]
            kvs = c[1]
            match = c[2]
            p = parse(sel)
            assert p.matches(kvs) == match, f"selector: '{sel}', kvs: '{kvs}'"
