## Romeo
This repository contains the source code for the Romeo compiler (detailed in this [paper](https://tinyurl.com/romeo-dac2020-authorversion)). Romeo is used to translate Verilog code to fully homomorphic circuits using [TFHE](https://tfhe.github.io/tfhe/) in order to facilitate secure computation outsourcing to the cloud. For more information about the theory behind Romeo, see [this presentation](https://tinyurl.com/romeo-dac2020-video-ppt). To reference this framework, please use the following citation for the accompanying paper: 

C. Gouert and N.G. Tsoutsos, "Romeo: Conversion and Evaluation of HDL Designs in the Encrypted Domain," *57th ACM/IEEE Design Automation Conference.* pp. 1--6, 2020.

#### Romeo Dependencies
Install [TFHE](https://tfhe.github.io/tfhe/) and ensure that SPQLIOS_FMA is chosen as an FFT engine (this can be done during the cmake configuration step).
Install [Yosys Open SYnthesis Suite](http://www.clifford.at/yosys/documentation.html). This can be done with the following commands:
```
$ sudo add-apt-repository ppa:saltmakrell/ppa
$ sudo apt-get update
$ sudo apt-get install yosys
```

## Synthesizing Verilog Programs for Romeo
Romeo expects a particular syntax in the EDIF files that it processes. To achieve the best results, use the following commands:
```
$ yosys
$ read_verilog <HDL_SOURCE_FILE>
$ proc
$ flatten
$ aigmap -nand
$ write_edif <NAME_OF_NETLIST>
```

For designs with multiple modules, you must execute a read_verilog command for each one.

## Generating Homomorphic Circuits from EDIF Netlists
The first step is to set environment variables and generate keys for yourself and the cloud. This can be done with the following commands:
```
$ make setenv
$ make keygen
```

Next, run the following command to generate an INSECURE homomorphic circuit for testing and also prepare encrypted inputs:
```
$ make prep_and_verif
```

This will create a directory called "inputs" that contains the encrypted inputs supplied during the previous step.
In addition, it will also generate a C++ program that can be used to verify correctness of the HE circuit.
Execute the following lines to run this program locally:
```
$ g++ -o <EXEC> <NAME_OF_CIRCUIT>.cpp -ltfhe-spqlios-fma
$ ./<EXEC>
```

Lastly, run the following command to generate a secure homomorphic circuit for the cloud to execute:
```
$ make generate
```

The above command will also generate a directory called "outputs" in which the cloud will store the encrypted results of the computations.
The final step is to upload the "inputs" and "outputs" directories to the cloud, the secure homomorphic circuit source file, and the "clouds.key" file generated in the key generation step. These commands can be used to run the circuit on the cloud:
```
$ g++ -o <EXEC> <NAME_OF_CIRCUIT>.cpp -ltfhe-spqlios-fma
$ ./<EXEC>
```

To remove generated files, type the following command:
```
$ make clean
```
