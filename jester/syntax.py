"""
HTTP protocol syntax elements.

These are taken from :rfc:`7230#appendix-B`.

"""

ALPHA = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
"""
Letters in the ASCII alphabet.

.. productionlist:: alpha
   alpha: "a" | "b" | "c" | "d" | "e" | "f" | "g" | "h" | "i" | "j"
        | "k" | "l" | "m" | "n" | "o" | "p" | "q" | "r" | "s" | "t"
        | "u" | "v" | "w" | "x" | "y" | "z" | "A" | "B" | "C" | "D"
        | "E" | "F" | "G" | "H" | "I" | "J" | "K" | "L" | "M" | "N"
        | "O" | "P" | "Q" | "R" | "S" | "T" | "U" | "V" | "W" | "X"
        | "Y" | "Z"

"""

DIGIT = '0123456789'
"""
Numbers in the ASCII alphabet.

.. productionlist: digit
   digit: "0" | "1" | "2" | "3" | "4" | "5" | "6" | "7" | "8" | "9"

"""

TCHARS = "!#$%&'*+-.^_`|~" + DIGIT + ALPHA
"""
Characters that may occur in a token.

.. productionlist:: token
   tchar: "!" | "#" | "$" | "%" | "&" | "'" | "*" | "+" | "-"
        | "." | "^" | "_" | "`" | "|" | "~" | `digit` | `alpha`
   token: 1* `tchar`

"""
