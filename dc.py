from PySpice.Spice.Netlist import Circuit
from PySpice.Unit import u_Ω, u_V
import matplotlib.pyplot as plt


def generate_circuit(netlist, voltage_value):
    
    circuit = Circuit('Generated Circuit')
    lines = netlist.split('\n')
    output_text = ''  # Metin tabanlı çıktıyı biriktirmek için boş bir string

    for line in lines:
        line = line.strip()
        if line.startswith('Resistor'):
            elements = line.split()
            name, node1, node2, value = elements[0], elements[1], elements[2], elements[3]

            number = ''.join(filter(str.isdigit, name))
            last_number = number.split("R")[0]

            value = value[:-1] + "@u_Ω"
            print(value)
            value = eval(value)  # Converts the value to a unit object
            circuit.R(last_number, node1, node2, value)

        elif line.startswith('Voltage_Source'):
            elements = line.split()
            name, node1, node2, value = elements[0], elements[1], elements[2], elements[3]
            number = ''.join(filter(str.isdigit, name))
            last_number = number.split("V")[0]

            value = voltage_value + "@u_V"

            value = eval(value)  # Converts the value to a unit object
            circuit.V(last_number, node1, node2, value)

    simulator = circuit.simulator(temperature=25, nominal_temperature=25)
    analysis = simulator.operating_point()

    for node in analysis.nodes.values():
        output_text += 'Node {}: {:5.1f} V\n'.format(str(node), float(node))
    for branch in analysis.branches.values():
        output_text += 'Branch {}: {:5.2f} A\n'.format(str(branch), float(branch))

    return output_text