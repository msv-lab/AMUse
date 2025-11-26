datalog_basics = """

The following are provided Datalog relations which you can use to write the Datalog detector.

===============================Datalog declarations=================================

.decl assert(x:number, in_method_signature:symbol)

// the 'var' is assigned a value at 'label' in the method signature 'in_method_signature'
.decl assigned(var:symbol, label:number, in_method_signature:symbol)

//the 'var' is assigned the 'value' at 'label' in the method signature 'in_method_signature'
.decl assignment(var:symbol, value:symbol, label:number, in_method_signature:symbol)

// the 'type' 'var' is defined at 'label' with the 'value' in the method signature 'in_method_signature'
.decl define(type:symbol, var:symbol, value:symbol, label:number, in_method_signature:symbol)

.decl catch(exception_type:symbol, exception_variable:symbol, catch_label:number, catch_body_start:number, catch_body_end:number, in_method_signature:symbol)

// index is the index of the argument in the method signature, starting from 0
.decl actual_argument(meth_sig:symbol, arg:symbol, label:number, index:number, in_method_signature:symbol)

.decl formal_argument(para: symbol, meth_start: number, index: number, in_meth_sig: symbol)

.decl final(x:number, in_method_signature:symbol)

.decl value(value:symbol, label:number, in_method_signature:symbol)

//direct successor
.decl succ(x:number, y:number, in_method_signature:symbol)

.decl true_succ(x:number, y:number, in_method_signature:symbol)

.decl false_succ(x:number, y:number, in_method_signature:symbol)

.decl constructor_call(constructor_signature:symbol, label:number, in_method_signature:symbol)

.decl call(call_sig:symbol, label:number, target:symbol, in_method_signature:symbol)

// 'meth_sig' is the method signature appearing in the method 'in_method_signature'
.decl method(meth_sig:symbol, in_method_signature:symbol)

// 'x' is the label of the return statement in the method 'in_method_signature'
.decl return(x:number, in_method_signature:symbol)

// 'value' is the return expression of the method 'in_method_signature'. 'x' is the label of the return statement.
.decl return_value(value:symbol, x:number, in_method_signature:symbol)

.decl start(x:number, in_method_signature:symbol)

.decl label(x:number, in_method_signature:symbol)

// 'x' and 'y' are the labels of the try region. It is NOT necessary that x < y.
.decl try(x:number, y:number, in_method_signature:symbol)

.decl finally(s_try: number, x: number, in_method_signature:symbol)

.decl variable(x:symbol, in_method_signature:symbol)

.decl static_method(meth_sig:symbol, y:number, in_method_signature:symbol)

.decl throw(label:number, thrown_expre:symbol, in_method_signature:symbol)

// operator: "L_NOT", "B_NOT", "NEG", "POS", "INC", "DEC"
.decl unary_op(operator:symbol, operand:symbol, label:number, in_method_signature:symbol)

// operator: "ADD", "SUB", "MUL", "DIV", "MOD", "AND", "OR", "BIT_AND", "BIT_OR", "BIT_XOR", "LSHIFT", "RSHIFT", "URSHIFT", "LT", "GT", "LE", "GE", "EQ", "NE", "INSTANCEOF"
.decl binary_op(left: symbol, operator: symbol, right: symbol, label: number, in_method_signature:symbol)

.decl if(label: number, in_method_signature:symbol)

.decl if_var(var: symbol, label: number, in_method_signature:symbol)

.decl while_condition(label: number, in_method_signature:symbol)

.decl while_condition_var(var: symbol, label: number, in_method_signature:symbol)

.decl for_condition(label: number, in_method_signature:symbol)

.decl for_condition_var(var: symbol, label: number, in_method_signature:symbol)

.decl assign_type(type: symbol, var: symbol, in_method_signature:symbol)

.decl defined(var:symbol, s:number, s_meth_sig:symbol)

.decl node(x: number, meth_sig: symbol)

// x must precede y, x -> AP y
.decl dom(x: number, x_meth_sig:symbol, y: number, y_meth_sig:symbol)

// x must follow y, x -> AF y
.decl post_dom(x: number, x_meth_sig:symbol, y: number, y_meth_sig:symbol)

// the transition from 's' to 't' is a transition that satisfies some condition 
.decl sat_transition(s: number, s_meth_sig: symbol, t: number, t_meth_sig: symbol)

// the variable 'var' satisfies some condition at 'label' in the method signature 'in_method_signature'
.decl var_condition(var: symbol, label: number, in_method_signature: symbol)


================================= Datalog declarations end ===============================

==================== Souffle Datalog Grammar notifcation ====================================

'!' is the symbol for negation in Souffle Datalog.

================================= Souffle Datalog Grammar end ===============================
"""

example_pairs_prompt = """
Please synthesize the Datalog detector for the {apis}.
The following are example pairs of correct and incorrect usages of the '{apis}'.

Usage example pairs:

{example_pairs}

"""

instruction_prompt = """

The above relations are common; you can define your own conditions and relations. Please output only the Datalog rules and the declarations that you have newly defined, and do not include any other information.
The standard api signature(s) is/are from the following list:
{all_api_sigs}

It is normal to have multiple correct usage patterns for an API. If you have multiple correct usage patterns, please think twice and only keep the most prevalent one.
Your Datalog rules should strictly follow the provided template.


Template:
correct_usage("api_sig", label1, var1, in_meth) :- //replace the api_sig with the actual api signature
    call("api_sig", label1, var1, in_meth), 
    yourOwnDefinedCondition1(...),
    ...

yourOwnDefinedCondition1(...):- //replace the name with a suitable condition name
    ...

incorrect_usage("api_sig", label1, var1, in_meth) :- 
    call("api_sig", label1, var1, in_meth), 
    !correct_usage("api_sig", label1, var1, in_meth).
"""


store = "Please use the 'flow' relation with caution when connecting API elements, as it only represents a direct flow connection in control flow analysis. You should consider 'dom', 'post_dom', 'sat_transition', 'var_condition' first when connecting API elements."
