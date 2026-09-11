# -*- coding: utf-8 -*-
"""
@author: Scott Greenwood

Copyright (c) 2024 UT-Battelle
Licensed under the terms of both the MIT license and the Apache License (Version 2.0).
Users may choose either license, at their discretion.
"""

import os
import sys
base_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(base_path,r'submodules/AutoCSM/AutoCSM'))
from auto_csm import AutoCSM
from pathlib import Path

if __name__ == "__main__":

    # Location of the JSON specifications
    datacenters = ['json/marconi100.json','json/lassen.json', 'json/summit.json']
    
    for datacenter in datacenters:
        
        # Instantiate AutoCSM
        csm = AutoCSM(language='modelica', architecture='nested')
        
        # You can turn off terminal animation if desired
        csm.terminal_animation = False
    
        # JSON describing the model
        csm.input_specification = datacenter
        
        # Set the path to output created files
        csm.output_path = Path('temp') / Path(datacenter).stem
    
        # Project path (path to Modelica library. This will also update the project name)
        csm.project_path = 'POWER9Datacenter'
        
        # Create architecture (if creating project from scratch)
        # csm.create_architecture()
    
        # Create the model for export to FMU (i.e., Simulator.mo)
        csm.create_model(uniform=[False, False])
         # Note this does not specify a solver in the model file. That is added in create_FMU.
    
        # Model dependencies: List of libraries needed for FMU generation or model setup scripts
        dependencies = [
            r'submodules/TRANSFORM-Library/TRANSFORM/package.mo'
            ]
        
        # Create the setup.mos file (optional)
        csm.create_setup(dependencies, compiler='dymola')
                
        # Generate the FMU (i.e., Simulator.fmu)
        csm.create_fmu(dependencies, experimentSettings={'solver':'Sdirk34hw','tolerance':1e-5}, includeVariables=None)