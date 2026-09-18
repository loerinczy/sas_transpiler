from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Token:
    type: str
    value: str
    line: int
    column: int


KEYWORDS = {
    "DATA",
    "PROC",
    "SQL",
    "SET",
    "WHERE",
    "IF",
    "THEN",
    "ELSE",
    "RUN",
    "QUIT",
    "SELECT",
    "FROM",
    "AS",
    "GROUP",
    "BY",
    "JOIN",
    "ON",
    "CREATE",
    "TABLE",
    "INSERT",
    "UPDATE",
    "DELETE",
    "KEEP",
    "DROP",
    "RENAME",
    "WORK",
    "INPUT",
    "OUTPUT",
    "MERGE",
    "RETAIN",
    "ARRAY",
    "DO",
    "END",
    "CASE",
    "WHEN",
    "THEN",
    "END",
    "IN",
    "NOT",
    "NULL",
    "AND",
    "OR",
    "XOR",
    "LIKE",
}

OPERATORS = {
    ">=",
    "<=",
    "~=",
    "!=",
    "=",
    ">",
    "<",
    "+",
    "-",
    "*",
    "/",
    "||",
    "&&",
    "&",
    "%",
    ".",
    ":",
    ",",
    "(",
    ")",
    ";",
}


class SASLexer:
    def tokenize(self, text: str) -> List[Token]:
        tokens: List[Token] = []
        index = 0
        line = 1
        column = 1

        while index < len(text):
            char = text[index]

            if char in "\r\n":
                if char == "\r" and index + 1 < len(text) and text[index + 1] == "\n":
                    index += 1
                line += 1
                column = 1
                index += 1
                continue

            if char.isspace():
                column += 1
                index += 1
                continue

            if char in {'"', "'"}:
                quote_char = char
                start_line = line
                start_col = column
                value = char
                index += 1
                column += 1
                while index < len(text):
                    current = text[index]
                    value += current
                    index += 1
                    column += 1
                    if current == quote_char:
                        break
                    if current == "\\" and index < len(text):
                        value += text[index]
                        index += 1
                        column += 1
                tokens.append(Token(type="STRING", value=value, line=start_line, column=start_col))
                continue

            if char.isdigit() or (char == "." and index + 1 < len(text) and text[index + 1].isdigit()):
                start_line = line
                start_col = column
                start = index
                while index < len(text) and (text[index].isdigit() or text[index] in "."):
                    index += 1
                    column += 1
                tokens.append(Token(type="NUMBER", value=text[start:index], line=start_line, column=start_col))
                continue

            if char.isalpha() or char in "_%&":
                start_line = line
                start_col = column
                start = index

                qualified = False
                while index < len(text):
                    current = text[index]
                    if current.isalnum() or current in "_%&":
                        index += 1
                        column += 1
                        continue
                    if current == "." and index + 1 < len(text) and (text[index + 1].isalpha() or text[index + 1] in "_%&"):
                        prefix_value = text[start:index]
                        prefix_upper = prefix_value.upper()
                        tokens.append(
                            Token(
                                type="KEYWORD" if prefix_upper in KEYWORDS else "IDENT",
                                value=prefix_upper if prefix_upper in KEYWORDS else prefix_value,
                                line=start_line,
                                column=start_col,
                            )
                        )
                        tokens.append(Token(type="OPERATOR", value=".", line=line, column=column))
                        index += 1
                        column += 1
                        member_start = index
                        while index < len(text):
                            nxt = text[index]
                            if nxt.isalnum() or nxt in "_%&":
                                index += 1
                                column += 1
                            else:
                                break
                        member_value = text[member_start:index]
                        member_upper = member_value.upper()
                        tokens.append(
                            Token(
                                type="KEYWORD" if member_upper in KEYWORDS else "IDENT",
                                value=member_upper if member_upper in KEYWORDS else member_value,
                                line=start_line,
                                column=member_start - start + start_col + 1,
                            )
                        )
                        qualified = True
                        break
                    break

                if not qualified:
                    value = text[start:index]
                    upper = value.upper()
                    token_type = "KEYWORD" if upper in KEYWORDS else "IDENT"
                    tokens.append(Token(type=token_type, value=upper if token_type == "KEYWORD" else value, line=start_line, column=start_col))
                continue

            op_match = None
            for op in sorted(OPERATORS, key=len, reverse=True):
                if text.startswith(op, index):
                    op_match = op
                    break
            if op_match is not None:
                start_line = line
                start_col = column
                tokens.append(Token(type="OPERATOR", value=op_match, line=start_line, column=start_col))
                index += len(op_match)
                column += len(op_match)
                continue

            tokens.append(Token(type="UNKNOWN", value=char, line=line, column=column))
            index += 1
            column += 1

        return tokens
