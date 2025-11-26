prompt_template = """
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

.decl flow(x:number, y:number, in_method_signature:symbol)

.decl true_flow(x:number, y:number, in_method_signature:symbol)

.decl false_flow(x:number, y:number, in_method_signature:symbol)

.decl constructor_call(constructor_signature:symbol, label:number, in_method_signature:symbol)

// call_sig is the qualified name of the method
.decl call(call_sig:symbol, label:number, target:symbol, in_method_signature:symbol)

// 'meth_sig' is the method signature appearing in the method 'in_method_signature'
.decl method(meth_sig:symbol, in_method_signature:symbol)

// 'x' is the label of the return statement in the method 'in_method_signature'
.decl return(x:number, in_method_signature:symbol)

// 'value' is the return expression of the method 'in_method_signature'. 'x' is the label of the return statement.
.decl return_value(value:symbol, x:number, in_method_signature:symbol)

.decl start(x:number, in_method_signature:symbol)

.decl label(x:number, in_method_signature:symbol)

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

// there exists a path that allows node x to reach node y. x_meth_sig and y_meth_sig are the methods where x and y in, respectively.
.decl flow_reach(x:number, x_meth_sig:symbol, y:number, y_meth_sig:symbol)

// node x is dominated by node y. x_meth_sig and y_meth_sig are the methods where x and y in, respectively.
.decl dom(x: number, x_meth_sig:symbol, y: number, y_meth_sig:symbol)

// node x is post-dominated by node y. x_meth_sig and y_meth_sig are the methods where x and y in, respectively.
.decl post_dom(x: number, x_meth_sig:symbol, y: number, y_meth_sig:symbol)

// the flow from 's' to 't' is a transition that satisfies some condition 
.decl sat_transition(s: number, s_meth_sig: symbol, t: number, t_meth_sig: symbol)

// the 'v' satisfies some condition at 'label' in the method signature 'in_method_signature'
.decl v_condition(v: symbol, label: number, in_method_signature: symbol)


================================= Datalog declarations end ===============================

==================== Souffle Datalog Grammar notifcation ====================================

'!' is the symbol for negation in Souffle Datalog.

================================= Souffle Datalog Grammar end ===============================


Generally, correct API usage involves essential API elements and those API elements should satisfy certain constraints. The common constraints include:

1.Call-order: If an API method is called at point 'a', another method should be called at some point 'b'. The position relationship between 'a' and 'b' is: for all paths from 'a', they must go through 'b' or vice versa. 

2.Condition-check: If an API method is called at point 'a', then another method must be called at point 'b' with a return value of true. For all paths that can reach 'a', they must first go through the state where the return value of the method is satisfiable.

3.Return value check: If an API method is called at point 'a' and its return value is used at point 'b', then the returned value should be checked before it is used. For all paths that can reach 'b', they must first go through the state where the returned value is satisfiable. The 'use' of the returned value includes passing it as an argument to another method or invoking a method on it.

4.Input value check: Sometimes, certain arguments of an API method should satisfy specific conditions. Therefore, these arguments should be checked before calling the method. If an API method is called at node 'a' and its argument 'arg_i' needs to satisfy certain condition, then 'arg_i' should be checked at some node 'b'. For all paths that can reach 'a', they must go through the state where the state of the 'arg_i' satisfies the condition.

5. Exception handling: If there is no condition check to ensure that an API method will not throw an exception, the API method call should be surrounded with a try-catch block.

The above API constraints describe common relations between API elements. These relations are optional, meaning that the API elements do not always need to satisfy one of the listed relations. They can also satisfy new relations not mentioned, or they may not satisfy any relation at all.

Now, please reflect the common usage patterns of the API '{api}' and summarize them. There may be multiple correct usage patterns for the API, but please only list the most common one.

Next, write the Souffle Datalog rules to describe the correct usage patterns.
First, identify the API elements and their relations. Then, write the Datalog rules to describe the relations.
For each pattern description, the subject(s) and object(s) are usually API elements. 
When you describe the relation between API elements, please use the following for the common relations:

Call-order: Assume the API method is called at 'x' in 'x_meth' and another necessary method is called at 'y' in 'y_meth'. If the necessary method must be called after the API method, their relation is:
post_dom(x, x_meth, y, y_meth), meaning that for all paths starting from the node 'x' in 'x_meth' to the exit node, they must go through 'y' in 'y_meth'. 
Conversely, if the necessary method must be called before the API method, their relation is: 
dom(x, x_meth, y, y_meth), meaning that for all paths from the entry node to 'x' in 'x_meth', they must go through 'y' in 'y_meth'.

Condition-check: Assume the API method is called at 'x' in 'x_meth' and the necessary method is called at 'y' in 'y_meth', with its return value assigned to a variable 'var' also at 'y' in 'y_meth'. For this pattern, the relation is: 
assigned(var, y, y_meth),
v_condition(var, y, y_meth),
sat_transition(y, y_meth, x1, x1_meth), 
dom(x, x_meth, x1, x1_meth),
call(the_api, x, the_var_call_the_api, x_meth). // the API call

Return value check: Assume the API method is called at 'label_call' in 'x_meth' with its return value assigned to a variable 'var' also at 'label_call' in 'x_meth', and the 'var' is used at 'label_use' in 'y_meth'.
For this pattern, the relation is:
call(the_api, label_call, the_var_call_the_api, x_meth), // the API call
assigned(ret_var, label_call, x_meth), // the return value of the API method is assigned to 'ret_var' at 'label_call' in 'x_meth'.
v_condition(ret_var, label_check, x0_meth),
sat_transition(label_check, x0_meth, label_sat, x1_meth),
dom(label_use, y_meth, label_sat, x1_meth), // 'label_use' in 'y_meth' is dominated by 'label_sat' in 'x1_meth'
(actual_argument(_, ret_var, label_use, _, y_meth);
call(_, label_use, ret_var, y_meth)).

Input value check: Assume the API method is called at 'x' in 'x_meth' with its argument 'arg_i' needing to satisfy a certain condition. For this pattern, when arg_i is a variable the relation is:
actual_argument(the_api, arg_i, x, _, x_meth), // the argument 'arg_i' of the API method
v_condition(arg_i, x, x_meth),
sat_transition(x0, x0_meth, x1, x1_meth),
dom(x, x_meth, x1, x1_meth),
call(the_api, x, the_var_call_the_api, x_meth). // the API call

When arg_i is a constant, the relation is:
actual_argument(the_api, arg_i, x, _, x_meth), // the argument 'arg_i' of the API method
v_condition(arg_i, x, x_meth), // the condition that 'arg_i' should satisfy
call(the_api, x, the_var_call_the_api, x_meth). // the API call

Exception handling: Assume the API method is called at 'x' in 'x_meth', with the try-catch structure at 'x0' and 'x1'. For this pattern, the relation is: 
flow_reach(x0, x_meth, x, x_meth), flow_reach(x, x_meth, x1, x_meth).


The above relations are common; you can define your own conditions and relations. Your Datalog rules should strictly follow the provided template. Note, v_condition(var, label, in_meth) is not a predefined relation. You must *implement* it according to the API if your rules require it.
Please only output the Datalog rules and do not include any other information.
It is normal to have multiple correct usage patterns for an API. If you have multiple correct usage patterns, please think twice and only keep the most prevalent ones.

Template:
correct_usage_i("{api}", label1, var1, in_meth) :- 
    call("{api}", label1, var1, in_meth), 
    yourOwnDefinedCondition1(...),
    ...

yourOwnDefinedCondition1(...):- //replace the name with a suitable condition name
    ...

v_condition(var1, label_2, in_meth):- 
    ...

"""

datalog_basics = """
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

.decl flow(x:number, y:number, in_method_signature:symbol)

.decl true_flow(x:number, y:number, in_method_signature:symbol)

.decl false_flow(x:number, y:number, in_method_signature:symbol)

.decl constructor_call(constructor_signature:symbol, label:number, in_method_signature:symbol)

.decl call(call_sig:symbol, label:number, target:symbol, in_method_signature:symbol)

.decl call_name(call_name:symbol, label:number, target:symbol, in_method_signature:symbol)

// 'meth_sig' is the method signature appearing in the method 'in_method_signature'
.decl method(meth_sig:symbol, in_method_signature:symbol)

// 'x' is the label of the return statement in the method 'in_method_signature'
.decl return(x:number, in_method_signature:symbol)

// 'value' is the return expression of the method 'in_method_signature'. 'x' is the label of the return statement.
.decl return_value(value:symbol, x:number, in_method_signature:symbol)

.decl start(x:number, in_method_signature:symbol)

.decl label(x:number, in_method_signature:symbol)

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

// x must precede y
.decl dom(x: number, x_meth_sig:symbol, y: number, y_meth_sig:symbol)

// x must follow y
.decl post_dom(x: number, x_meth_sig:symbol, y: number, y_meth_sig:symbol)

// the flow from 's' to 't' is a transition that satisfies some condition 
.decl sat_transition(s: number, s_meth_sig: symbol, t: number, t_meth_sig: symbol)

// the variable 'var' satisfies some condition at 'label' in the method signature 'in_method_signature'
.decl v_condition(var: symbol, label: number, in_method_signature: symbol)


================================= Datalog declarations end ===============================

==================== Souffle Datalog Grammar notifcation ====================================

'!' is the symbol for negation in Souffle Datalog.

================================= Souffle Datalog Grammar end ===============================
"""

pattern_prompt_template = """
Generally, correct API usage involves essential API elements and those API elements should satisfy certain constraints. The common constraints include:

1.Call-order: If an API method is called at point 'a', another method should be called at some point 'b'. The position relationship between 'a' and 'b' is: for all paths from 'a', they must go through 'b' or vice versa. 

2.Condition-check: If an API method is called at point 'a', then another method must be called at point 'b' with a return value of true. For all paths that can reach 'a', they must first go through the state where the return value of the method is satisfiable.

3.Return value check: If an API method is called at point 'a' and its return value is used at point 'b', then the returned value should be checked before it is used. For all paths that can reach 'b', they must first go through the state where the returned value is satisfiable. The 'use' of the returned value includes passing it as an argument to another method or invoking a method on it.

4.Input value check: Sometimes, certain arguments of an API method should satisfy specific conditions. Therefore, these arguments should be checked before calling the method. If an API method is called at node 'a' and its argument 'arg_i' needs to satisfy certain condition, then 'arg_i' should be checked at some node 'b'. For all paths that can reach 'a', they must go through the state where the state of the 'arg_i' satisfies the condition.

5. Exception handling: If there is no condition check to ensure that an API method will not throw an exception, the API method call should be surrounded with a try-catch block.

The above API constraints describe common relations between API elements. These relations are optional, meaning that the API elements do not always need to satisfy one of the listed relations. They can also satisfy new relations not mentioned, or they may not satisfy any relation at all.

Now, please reflect the common usage patterns of the API '{api}' and summarize them. There may be multiple correct usage patterns for the API, but please only list the most common ones and do not include any other information. For a usage pattern, you can describe the relations between API elements or the constraints that the API elements should satisfy. If the relations involve the above common constraints, please explicitly mention them. 
Note, each usage pattern should only describe one relation or constraint. If you have multiple relations or constraints, please describe them in separate usage patterns. Please follow the template below.

Template:

usage pattern 1 title
involved common constraints // if any. only list the names of the constraints
description of the usage pattern

...

"""

concise_pattern_prompt_template = """Describe the most common usage pattern(s) for the API '{api}'. For each pattern, use the template:

API element, relationship [condition], API element.

First API element: the first API element in the pattern.
Second API element: the second API element in the pattern.
relationship: the relationship between the API elements in the pattern.
[condition]: the condition that the API elements should satisfy in the pattern.


Where:
- API element: A method, return value, or argument of the API
- relationship: How the elements are connected (e.g., "must be called before", "must be called after", "is passed to")
- [condition]: Optional specific condition, if applicable (e.g., "if not null", "greater than 0", "on success")

List only the most essential pattern(s). Avoid explanations or additional details.
"""