# AMUse

Patching Java Programs with Datalog

## Set up

To build a Docker image of this repository and run it on Docker you need to build the image:

    docker build . -t amuse

## Usage

There are three stages to this project, specfication mining, detection of misuses and patcher.

### Building the Docker Image

To run the project

    docker run -it -v $PWD/src:/amuse/src -v $PWD/.env:/amuse/.env -v $PWD/input:/amuse/input -v $PWD/output:/amuse/output --rm amuse

The command above maps the src, input and output folders as ell as the env file that you could configure the settings for the project.

### Getting facts from a java file

To only run the detection phase and extract only the facts from a java file run the command below.

    docker run -it -v $PWD/src:/amuse/src -v $PWD/.env:/amuse/.env -v $PWD/input:/amuse/input -v $PWD/output:/amuse/output --rm amuse ./amuse -facts *path to your java file*

### Running the Synthesiser from a java file or files

check the file `src/amuse/synthesiser.py` for running the synthesiser.

### Clean the output folder


    docker run -it -v $PWD/src:/amuse/src -v $PWD/.env:/amuse/.env -v $PWD/input:/amuse/input -v $PWD/output:/amuse/output --rm amuse ./amuse -clean

### Running Target Mode

Then to run the patcher run the following code below. Note that the project should be built and provided with classpath initially.

        docker run -it -v $PWD/src:/amuse/src -v $PWD/.env:/amuse/.env -v $PWD/input:/amuse/input -v $PWD/output:/amuse/output --rm amuse ./amuse -target *path to your java project*

## Input Language

The input language of this project is Java

## Datalog Relations Specification

The specification miner will produce the analyses as datalog programs. In the **detection of misuses** stage we transform the set of source code in the root `src` folder to `*.facts` in the `/detector/facts`. Where * are the relations specified below.

* `arguments(V, N)` is a value used in a method argument
* `assert(N)`: `N` is the node where the assert with condition is called
* `assign_type(T, V)` `T` is a type of the value `V`
* `assign(V, N)`: a value is assigned to the variable `V` at node `N`
* `condition(N)`: `N` is the node where a branch occurs from loops or if conditions
* `conjunction(N)`: `N` is the node where a conjunction condition occurs 
* `defined(V,N)`: `V` the variable being assigned a value at node `N`
* `depth_statement(D, N)`: `D` is the integer value of how many nested block the node `N` is in
* `disjunction(N)`: `N` is the node where a disjunction condition occurs 
* `end(N)`: `N` is the node to the exit point of the program
* `exceptions_hierchy(E1, E2)`: `E1` is the exception and `E2` is the parent Exception of `E1`.
* `exceptions_pos(E, N)`: `E` is the exception for the catch block at node `N`.
* `exceptions(E)`: `E` are the exceptions.
* `flow(N1, N2)`: there is an edge between node 1(`N1`) and node 2(`N2`) from the cfg graph
* `true_flow(N1, N2)`: the true flow from a condition. where `N1` is where the condition node is and
`N2` is the first node in that true branch
* `false_flow(N1, N2)`: the false flow from a condition. where `N1` is where the condition node is and
`N2` is the first node in that false branch
* `initialisation(C,N)`: a new instance of class `C` is created at node `N`
* `instance_call(V,M,N)`: variable `V` calls method `M` is called at statement of the program at node `N`
* `instance_variables(V,M,N)`: variable `V` calls method `M` is called at statement of the program at node `N`
* `method(M)`: `M` is the full method name used. Methods are named such as `java.io.ObjectOutputStream.close` et cetera...
* `negation(N)`: `N` is the condition line that utilises a bang(!) negation operator
* `not_null_check(V, N)`: `V` is the variable being check that it is not null (!= null) on node `N`
* `null_check(V, N)`: `V` is the variable being check that it is not null (== null) on node `N`
* `return_value(V, N)`: node `N` where the return call is made and `V` is the value that is returned
* `return(N)`: node `N` where the return call is made
* `start(N)`: `N` is the node to the entry point of the program
* `statement(N)`: `N` is a node label of the statement. It is just a number
* `static_method(M, N)`: `M` is the full method name used and `N` is there node where static method call was used. Methods are named such as `java.io.ObjectOutputStream.close` et cetera...
* `throw(N)`: `N` is the node where throw is called
* `try(N1,N2)`: `N1` is the node where the try block is started and `N2` is the node where the exception is started
* `variable(V)`: `V` is a variable name


<!-- archived -->
* `conjunction(L, R, N)`: left expression/variable `L` and right expression/variable `R` is a conjunctive condition. eg if (x() && y())

* `disjunction(L, R, N)`: left expression/variable `L` and right expression/variable `R` is a disjunctive condition at node `N`. eg if (x || y)


## Data

MUBench source projects: https://drive.google.com/file/d/1FIMQ7-4nlOd7ZQxYvxvpTG-Z8gA3j32s/view?usp=drive_link
