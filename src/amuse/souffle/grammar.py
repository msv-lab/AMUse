souffle_grammar = """
    start: (declaration | rule | directive | output | input)*
    directive: "#" NAME ESCAPED_STRING
    declaration: ".decl" NAME "(" [typed_var ("," typed_var)*] ")"
    output: ".output" NAME
    input: ".input" NAME
    typed_var: NAME ":" NAME
    ?arg: NAME -> var
        | value
    ?value: string
          | SIGNED_NUMBER -> number
    string : ESCAPED_STRING
    rule: literal [ ":-" body] "."
    ?literal: NAME "(" [arg ("," arg)*] ")" -> atom
            | "!" NAME "(" [arg ("," arg)*] ")"  -> negated_atom
            | arg "=" arg -> unification
            | arg "!=" arg -> negated_unification
    body: literal ("," literal)*
    COMMENT: /\/\/.*/
    %import common.CNAME -> NAME
    %import common.ESCAPED_STRING
    %import common.SIGNED_NUMBER
    %import common.WS
    %ignore WS
    %ignore COMMENT
"""
