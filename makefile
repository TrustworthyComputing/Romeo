install_tfhe:
	sudo apt-get install build-essential cmake cmake-curses-gui
        git clone https://github.com/tfhe/tfhe.git
	cd tfhe
	mkdir build
	cd build
	ccmake ../src
	make
	make install

setenv:
	TFHE_PREFIX=/usr/local
	export C_INCLUDE_PATH=$C_INCLUDE_PATH:$TFHE_PREFIX/include
	export CPLUS_INCLUDE_PATH=$CPLUS_INCLUDE_PATH:$TFHE_PREFIX/include
	export LIBRARY_PATH=$LIBRARY_PATH:$TFHE_PREFIX/lib
	export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$TFHE_PREFIX/lib

keygen: keygen.c
	gcc -o keygen keygen.c -ltfhe-spqlios-fma
	./keygen

prep_and_verif: gen_circuit_verif.py
	python3 gen_circuit_verif.py
	g++ -o input_gen input.cpp -ltfhe-spqlios-fma
	mkdir inputs
	./input_gen

generate: gen_circuit_secure.py
	mkdir outputs
	python3 gen_circuit_secure.py

clean:
	rm input_gen
	rm input.cpp
	rm -rf inputs
	rm -rf outputs
