import subprocess
import sys

class Port:
    # Defines input and output ports
    def __init__(self, name, direction, length):
        self.name = name
        self.direction = direction # input or output
        self.length = length # number of wires/bits
        self.nets = [""] * self.length # wires in the port

    def mapNet(self, net): # associate wires with ports
        for i in nets:
            if self.nets[i] == "":
                self.nets[i] = net.name

    def printPort(self): # debugging function
        print("\nPort ID: " + self.name)
        print("Direction: " + self.direction)
        print("# of Wires: " + str(self.length))
        index = 0
        for i in self.nets:
            if i != "":
                print(str(index) + ": " + i)
            index = index + 1

class LogicGate:
    def __init__(self, function, id):
        self.function = function # operation (i.e. XOR, AND, ...)
        self.id = id # identifier assigned by Yosys
        self.inputNets = [] # input wires (usually 2, but 1 for NOT, and 3 for MUX)
        self.outputNets = [] # output wires (usually 1)
        self.dependsOn = [] # gates immediately preceding the current gate
        self.dependsOnFF = False # used to determine if evaluation needs to repeat each clock cycle
        self.isEncrypted = False # used to check if gate evaluation occurred already
        self.next_state = "" # only used for sequential components

    def setInputNets(self, inNet):
        # associate wire with input of logic gate
        self.inputNets.append(inNet)
        for i in inNet.left:
            self.dependsOn.append(i)

    def setOutputNet(self, outNet):
        # associate wire with output of logic gate
        self.outputNets.append(outNet)


class Net:
    def __init__(self, name):
        self.name = name # identifier assigned by Yosys
        self.left = [] # this net is the output of these gates
        self.right = [] # gates for which this net is an input
        self.encValue = 0 # points to the ciphertext on the current wire
        self.value = "" # plaintext input (only applicable for input nets)

    def setLeft(self, leftGate):
        # associate wire as the output of a gate
        self.left.append(leftGate)

    def setRight(self, rightGate):
        # associate wire as the input of a gate
        self.right.append(rightGate)

def encryptInputs(netList):
    # prompts user for initial values of inputs
    for net in netList:
        if (len(net.left) == 0): # checks if net is an input
            net.value = str(input("Enter the input value of " + net.name + ": "))
            subprocess.call("./encrconst.bashrc " + net.value, shell=True)
            net.encValue = int(subprocess.check_output(['grep', '-c', '$', 'ctxtMem.txt']))

def checkFFDependency(gate, gateList):
    # check if gate is a FF
    if "dff" in gate.function:
        return True

    # check if gate is an input
    elif len(gate.dependsOn) == 0:
        return False

    else:
        for prev_gate in gate.dependsOn: # check if direct descendants are FFs
            if "dff" in prev_gate.function:
                return True

        for prev_gate in gate.dependsOn: # second pass, checks deeper using recursion
            if checkFFDependency(prev_gate, gateList) == True:
                return True

    return False

def main():
    inputFile = str(input("Please enter the filename of an EDIF netlist: "))
    outputFile = str(input("Please enter a filename for the generated circuit (.cpp): "))
    edif_file = open(inputFile, "r")
    tfhe_file = open(outputFile, "w")
    timeSteps = int(input("Enter the number of timesteps: ")) # number of cycles
    currentTime = 0

    # populate preamble
    print("populating preamble...")

    tfhe_file.write("#include <iostream>\n")
    tfhe_file.write("#include <tfhe/tfhe.h>\n")
    tfhe_file.write("#include <tfhe/tfhe_io.h>\n")
    tfhe_file.write("#include <stdio.h>\n")
    tfhe_file.write("#include <stdlib.h>\n")
    tfhe_file.write("#include <string.h>\n\n")

    tfhe_file.write("using namespace std;\n\n")
    tfhe_file.write("int main(int argc, char** argv) {\n\n")
    tfhe_file.write('''   FILE* cloud_key = fopen("clouds.key", "rb");\n''')
    tfhe_file.write('''   TFheGateBootstrappingCloudKeySet* bk = new_tfheGateBootstrappingCloudKeySet_fromFile(cloud_key);\n''')
    tfhe_file.write('''   fclose(cloud_key);\n\n''')
    tfhe_file.write('''   const TFheGateBootstrappingParameterSet* params = bk->params;\n\n''')


    flag = 0
    interfaceFlag = 0
    cellDFFFlag = 0
    indexFlag = 0
    portFlag = 0
    genericCounter = 0
    wireMapFlag = 0
    renameFlag = 1
    mapFlag = 0
    arrayFlag = 0
    cellCounter = 0
    nameFlag = 0
    prevWord = "ERROR"
    tempName = ""
    gateList = []
    portList = []
    cellList = []
    netList = []

    print("parsing EDIF netlist...")
    print("Declaring nets and gates...")
    for line in edif_file:
        isRight = 0
        isLeft = 0

        # ignore certain declarations
        if "GND" in line or "VCC" in line or "VDD" in line or "CK" in line:
            continue

        # get names of cells
        if "cell" in line and not flag and ("GENERIC" not in line) and (cellDFFFlag == 0):
            cellName = False
            if "(rename" not in line:
                cellName = True
            for word in line.split():
                if "id" in word:
                    cellName = True
                    continue
                elif "cell" in word:
                    continue
                elif cellName:
                    tempWord = word
                    tempWord = ''.join([i for i in tempWord if i.isalpha()])
                    cellList.append(tempWord)
                    cellName = False

        if "DESIGN" in line:
            flag = 1

        if "cell dff" in line: # special case for flip flops
            flag = 0
            cellDFFFlag = 1
            continue

        if "GENERIC" in line and cellDFFFlag:
            genericCounter = genericCounter + 1

        if genericCounter == 2:
            flag = 1

        if flag and "portRef" in line: # check if port is being referenced
            if ("instanceRef" not in line) and ("member" not in line):
                wireMapFlag = 1

        if flag and "interface" in line:
            interfaceFlag = 1

        # map net to port
        if ("net" in line) and ("rename" in line) and ("$" not in line) and flag:
            mapFlag = 1
        elif ("portRef" in line) and ("(member" in line) and flag:
            mapFlag = 1
        elif ("net" in line) and ("rename" not in line) and ("joined" in line):
            mapFlag = 1
            renameFlag = 0

        if flag and "GENERIC" in line:
            cellCounter = cellCounter + 1
        if cellCounter > 1: # ignore subsequent cells
            break
        if "net" in line or "portRef" in line:
            isNet = 1
            isInstance = 0
            isDeclare = 0
        elif "instance" in line:
            isInstance = 1
            isNet = 0
            isDeclare = 0
        elif "cellRef" in line and "GENERIC" not in line:
            isInstance = 0
            isNet = 0
            isDeclare = 1
        else:
            isInstance = 0
            isNet = 0
            isDeclare = 0

        for word in line.split():

            if wireMapFlag:
                prevWord_2 = ""
                for word_2 in prevLine.split():
                    if "id" in word_2:
                        tempName = word_2.strip(')')
                    elif "net" in prevWord_2:
                        tempName = word_2.strip(')')
                    prevWord_2 = word_2

                if "portRef" in prevWord:
                    for i in portList:
                        if i.name == word.strip(')'):
                            if "(instanceRef" in prevLine:
                                i.nets[0] = word.strip(')')
                            else:
                                i.nets[0] = tempName

                    wireMapFlag = 0

            # identify input and output ports
            if interfaceFlag and "port" in word:
                portFlag = 1
            elif interfaceFlag and portFlag and "array" in word:
                arrayFlag = 1
            elif interfaceFlag and portFlag and ("array" not in word) and ("port" in prevWord):
                tempName = word
                tempLength = 1
            elif interfaceFlag and portFlag and arrayFlag and not nameFlag:
                tempName = word
                nameFlag = 1
            elif interfaceFlag and portFlag and arrayFlag and nameFlag and "direction" not in word and \
                    "INPUT" not in word and "OUTPUT" not in word:
                tempLength = int(word.strip(')'))
            elif interfaceFlag and "direction" in prevWord:
                newPort = Port(tempName, word.strip(')'), tempLength)
                portList.append(newPort)
                portFlag = 0
                arrayFlag = 0
                nameFlag = 0

            # port mapping
            if mapFlag and (not renameFlag) and ("net" in prevWord):
                for i in portList:
                    if i.name == word:
                        i.nets[0] = word
                        break
                mapFlag = 0
                renameFlag = 1

            if mapFlag and "id" in word:
                tempName = word
            elif mapFlag and "member" in prevWord:
                portName = word
                indexFlag = 1
            elif mapFlag and indexFlag:
                index = word.strip(')')
                indexFlag = 0

                for word_2 in prevLine.split():
                    if "id" in word_2:
                        tempName = word_2

                for i in portList:
                    if i.name == portName:
                        i.nets[int(index)] = tempName
                        break
                mapFlag = 0

            elif mapFlag and "id" in prevWord:
                portName = word.strip('"')
                portName = portName.strip(')')
                index = ""
                inBrackets = False
                for character in portName:
                    if character == '[':
                        inBrackets = True
                    elif character == ']':
                        inBrackets = False
                    elif inBrackets:
                        index = index + character

                for i in portList:
                    if i.name == word:
                        i.nets[int(index)] = tempName
                        break

                mapFlag = 0

            if "contents" in word:
                interfaceFlag = 0

            if isInstance and "id" in word:
                prevID = word
            elif isInstance and "rename" not in line and "instance" not in word:
                prevID = word
            elif "id" in word and flag and isDeclare:
                index = int(word[-1]) - 1
                newGate = LogicGate(cellList[index], prevID)
                gateList.append(newGate)
            elif isDeclare and "(cellRef" in prevWord and flag and "DESIGN" not in line:
                newGate = LogicGate(word.strip(')'), prevID)
                gateList.append(newGate)

            elif isNet and ("net" in prevWord) and ("rename" not in word):
                newNet = Net(word)
                tfhe_file.write("   LweSample* " + word + " = new_gate_bootstrapping_ciphertext_array(1, params);\n")
                netList.append(newNet)
            elif isNet and ("rename" in prevWord):
                newNet = Net(word)
                tfhe_file.write("   LweSample* " + word + " = new_gate_bootstrapping_ciphertext_array(1, params);\n")
                netList.append(newNet)
            elif isNet and (word == "A" or word == "B" or word == "C" or word == "D"):
                isRight = 1
                isLeft = 0
            elif isNet and (word == "Y" or word == "Q"):
                isLeft = 1
                isRight = 0
            elif isNet and ("instanceRef" in prevWord):
                for gate in gateList:
                    if (gate.id in word):
                        if (isLeft):
                            newNet.setLeft(gate)
                        elif (isRight):
                            newNet.setRight(gate)
            prevWord = word
        prevLine = line

    print("Establishing connections between nets and gates...")
    print(cellList)
    for gate in gateList:
        for net in netList:
            for leftGate in net.left:
                if (leftGate.id == gate.id):
                    gate.setOutputNet(net)
            for rightGate in net.right:
                if (rightGate.id == gate.id):
                    gate.setInputNets(net)

    edif_file.close()

    print("Finished parsing netlist!")
    print("Removing redundancies...")

    for gate in gateList:
        gate.dependsOnFF = checkFFDependency(gate, gateList)

    redundancyCounter = 0
    for gate in gateList:
        if gate.dependsOnFF == False:
            redundancyCounter += 1

    print("Removed",redundancyCounter,"gate redundancies.")

    print("Preparing input values: ")

    for port in portList:
        isValid = False
        userInput = ""
        if "INPUT" in port.direction:
            counter = port.length - 1
            tfhe_file.write('\n')
            for i in range(port.length):
                tfhe_file.write('''   FILE* ''' + port.nets[counter] + '''_file = fopen("inputs/''' + port.nets[counter] + '''.ctxt", "rb");\n''')
                tfhe_file.write('''   import_gate_bootstrapping_ciphertext_fromFile(''' + port.nets[counter] + '''_file, &''' + port.nets[counter] + '''[0], params);\n''')
                tfhe_file.write('''   fclose(''' + port.nets[counter] + '''_file);\n''')
                counter = counter - 1


    print("Encrypting gates...")

    for gate in gateList:
        # print(gate.id)
        print(gate.function)
        # print(gate.inputNets)
        # print(gate.outputNets)
        print(gate.dependsOnFF)
        print()
    #encrypt all gates
    for clock in range(timeSteps):
        print("Timestep",clock)
        if clock == 0:
            encCounter = 0
            for logicGate in gateList:
                logicGate.isEncrypted = False
                if "dff" in logicGate.function or logicGate.function == "FD1":
                    if clock == 0:
                        tfhe_file.write("   bootsCONSTANT(&" + gate.outputNets[0].name + "[0], 0, bk);\n")
                        logicGate.isEncrypted = True
                        encCounter += 1
                    else:
                        tfhe_file.write("   bootsCOPY(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[
                            0].name + "[0], bk);\n")
                        logicGate.isEncrypted = True
                        encCounter += 1

        else: # exclude redundant gates
            encCounter = redundancyCounter
            for logicGate in gateList:
                if logicGate.dependsOnFF:
                    logicGate.isEncrypted = False
                if "dff" in logicGate.function or logicGate.function == "FD1":
                    if clock == 0:
                        tfhe_file.write("   bootsCONSTANT(&" + gate.outputNets[0].name + "[0], 0, bk);\n")
                        logicGate.isEncrypted = True
                        encCounter += 1
                    else:
                        tfhe_file.write("   bootsCOPY(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[
                            0].name + "[0], bk);\n")
                        logicGate.isEncrypted = True
                        encCounter += 1


        while encCounter < len(gateList):
            for gate in gateList:
                if (gate.isEncrypted == True):
                    continue
                if (len(gate.dependsOn) == 0):

                    if (gate.function == "AND" or gate.function == "AN2"):
                        tfhe_file.write("   bootsAND(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "OR"):
                        tfhe_file.write("   bootsOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "NOT" or gate.function == "IV"):
                        tfhe_file.write("   bootsNOT(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], bk);\n")
                    elif (gate.function == "NAND" or gate.function == "ND2"):
                        tfhe_file.write("   bootsNAND(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "NOR" or gate.function == "NR2"):
                        tfhe_file.write("   bootsNOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "XOR"):
                        tfhe_file.write("   bootsXOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "XNOR"):
                        tfhe_file.write("   bootsXNOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")

                    gate.isEncrypted = True

                    encCounter = encCounter + 1

                else:
                    encflag = 0
                    for prevGate in gate.dependsOn:
                        if (prevGate.isEncrypted == False):
                            encflag = 1
                            break

                    if (encflag == 1):
                        continue

                    if (gate.function == "AND" or gate.function == "AN2"):
                        tfhe_file.write("   bootsAND(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "OR"):
                        tfhe_file.write("   bootsOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "NOT" or gate.function == "IV"):
                        tfhe_file.write("   bootsNOT(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], bk);\n")
                    elif (gate.function == "NAND" or gate.function == "ND2"):
                        tfhe_file.write("   bootsNAND(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "NOR" or gate.function == "NR2"):
                        tfhe_file.write("   bootsNOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "XOR"):
                        tfhe_file.write("   bootsXOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")
                    elif (gate.function == "XNOR"):
                        tfhe_file.write("   bootsXNOR(&" + gate.outputNets[0].name + "[0], &" + gate.inputNets[0].name +
                                        "[0], &" + gate.inputNets[1].name + "[0], bk);\n")


                    gate.isEncrypted = True

                    encCounter = encCounter + 1

    tfhe_file.write('\n')
    for port in portList:
        if "OUTPUT" in port.direction:
            for i in range(port.length):
                tfhe_file.write('''   FILE* ''' + port.nets[i] + '''_file = fopen("outputs/''' + port.nets[i] + '''.ctxt","wb");\n''')
                tfhe_file.write('''   export_gate_bootstrapping_ciphertext_toFile(''' + port.nets[i] + '''_file, &''' + port.nets[i] + '''[0], params);\n''')
                tfhe_file.write("   fclose(" + port.nets[i] + "_file);\n")
    tfhe_file.write('\n')

    for net in netList:
        tfhe_file.write("   delete_gate_bootstrapping_ciphertext_array(1, " + net.name + ");\n")

    tfhe_file.write("   return 0;\n")
    tfhe_file.write("}\n")
    tfhe_file.close();

    print("Finished generating TFHE circuit!")

main()
