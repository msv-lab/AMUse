# Detector

## The detector will receive the datalog IDB synthesised from the specification miner and be queried against the facts(EDB) extracted from the java source code

## Usage

To extract the EDB from the java source code you should store the program with possible misuse in the root **src** folder.

Run `sh get_cfg_facts.sh /amuse/src/ammuse/{filename.java}` This will execute the bash script to extract the facts from the source code. There are three stages to this

- uses spoon and the CallGraphGenerator to generate the JSON representation(/amuse/detector/json) of the usage of the API call

- get_facts convert the JSON representation into EDB format suitable for use with Souffle (/amuse/detector/facts)

- To detect violations use the specification mined in the form of datalog to be executed with our facts extracted from the **specification miner** stored in the **specifications folder**. This will output the results in the output folder(/amuse/detector/output)

### Specification Format

Currently uses the sample put_flip.dl
