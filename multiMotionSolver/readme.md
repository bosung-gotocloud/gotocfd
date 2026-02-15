# Nested sliding meshes using OpenFOAM multiMotion Solver
[![Video Title](https://img.youtube.com/vi/FaP2jB4K5x0/0.jpg)](https://www.youtube.com/watch?v=FaP2jB4K5x0)

To simulate complex kinematics such as helicopter rotor cyclic pitch motion, a nested sliding mesh configuration—utilizing a sliding mesh inside another sliding mesh—is implemented using the OpenFOAM multiMotion solver.

For example, in helicopter simulations, two distinct rotations have to be dealt with 

- Primary Rotation: The entire rotor disk spinning around the hub.
- Cyclic Pitch: Each individual blade pitching up and down as it rotates.

By nesting a small cylindrical sliding zone (for the pitch) inside a larger rotating disk zone (for the main rotation), the multiMotion solver can calculate the relative velocities at both interfaces simultaneously.

## Example: Two blades cyclic pitch motion
This example implements a primary rotor rotation coupled with synchronized cyclic pitching for two opposing blades based on standard helicopter control theory.

### 1. Primary Rotation (Hub)

- Center of Rotation: (0, 0, 0)
- Rotation Axis: $+z$ axis
- Rotational Speed: 2000 RPM (calculated as $\omega \approx 209.4395 \text{ rad/s}$)

### 2. Blade Cyclic Pitch Motion

The blade pitch angle is governed by two complementary mathematical descriptions. First, the movement is defined by the longitudinal and lateral cyclic components:

$$\theta(\psi) = 10^\circ - 3^\circ \cos(\psi) - 2^\circ \sin(\psi)$$

Where:

$\theta_0$ (Collective Pitch): $10^\circ$

$\theta_{1c}$ (Longitudinal Cyclic): $3^\circ$

$\theta_{1s}$ (Lateral Cyclic): $2^\circ$ 

In the OpenFOAM [cyclicPitchMotion](https://github.com/bosung-gotocloud/gotocfd/blob/main/cyclicPitchMotionSolver/readme.md) solver, this is implemented using the amplitude-phase form:

$$\alpha(\theta) = \alpha_0 + A \sin(\theta + \phi)$$

The conversion from the control inputs to the solver parameters is as follows:

- Collective Pitch ($\alpha_0$): $10^\circ$

- Cyclic Amplitude ($A$): $\sqrt{3^2 + 2^2} = \mathbf{3.60555^\circ}$

- Phase ($\phi$): $atan2(-2, -3) \approx \mathbf{3.7296}$ rad (approx. $213.69^\circ$)

### 3. Critical Pitch Angles & Azimuth Positions

By solving the motion function, we identify the peak aerodynamic angles:

- Maximum Pitch Angle: $10^\circ + 3.60555^\circ = \mathbf{13.60555^\circ}$
    - Occurs at Azimuth $\psi \approx 306.31^\circ$ (where $\sin(\theta + \phi) = 1$)

- Minimum Pitch Angle: $10^\circ - 3.60555^\circ = \mathbf{6.39445^\circ}$
    - Occurs at Azimuth $\psi \approx 126.31^\circ$ (where $\sin(\theta + \phi) = -1$)

- Blade 180: Positioned exactly opposite, it utilizes a $180^\circ$ ($\pi$ rad) phase offset ($\phi \approx 0.5880$ rad) to maintain physical symmetry.

### 4. dynamicMeshDict Implementation

The dynamicMeshDict for this example is as follows:

```
/*--------------------------------*- C++ -*----------------------------------*\
| =========                 |                                                 |
| \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox           |
|  \\    /   O peration     | Version:  v2312                                 |
|   \\  /    A nd           | Website:  www.openfoam.com                      |
|    \\/     M anipulation  |                                                 |
\*---------------------------------------------------------------------------*/
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      dynamicMeshDict;
}

dynamicFvMesh dynamicMultiMotionSolverFvMesh;

rotation
{
    solidBodyMotionFunction  rotatingMotion;
    rotatingMotionCoeffs
    {
        origin (0 0 0);
        axis (0 0 1);
        omega 209.4395; 
    }
}

dynamicMultiMotionSolverFvMeshCoeffs
{
    rotorzone
    {
        solver          solidBody;
        cellZone        rotorzone;
        solidBodyCoeffs
        {
            $rotation;
        }
    }

    bladezone000
    {
        cellZone        bladezone000;
        solver          solidBody;
        solidBodyCoeffs
        {
            solidBodyMotionFunction multiMotion;
            multiMotionCoeffs
            {
                rotorRotation { $rotation; }
                pitchMotion
                {
                    solidBodyMotionFunction cyclicPitchMotion;
                    cyclicPitchMotionCoeffs
                    {
                        origin    (0 0 0);
                        axis      (1 0 0);   
                        omega     209.4395;  
                        amplitude 3.60555;   // Result of sqrt(3^2 + 2^2)
                        phase     3.7296;    // Result of atan2(-2, -3)
                        alpha0    10;        // Collective 10 degrees
                    }
                }
            }
        }
    }

    bladezone180
    {
        cellZone        bladezone180;
        solver          solidBody;
        solidBodyCoeffs
        {
            solidBodyMotionFunction multiMotion;
            multiMotionCoeffs
            {
                rotorRotation { $rotation; }
                pitchMotion
                {
                    solidBodyMotionFunction cyclicPitchMotion;
                    cyclicPitchMotionCoeffs
                    {
                        origin    (0 0 0);
                        axis      (-1 0 0);  
                        omega     209.4395;
                        amplitude 3.60555;
                        phase     0.5880;    // 3.7296 - PI
                        alpha0    10;
                    }
                }
            }
        }
    }
}
// ************************************************************************* //
```

Technical Item Descriptions are as follow:
- `dynamicMultiMotionSolverFvMesh`: The master class used to manage different motions across various mesh regions (`cellZones`).

- `solidBodyMotionFunction multiMotion`: A motion function that allows a `cellZone` to inherit a parent motion (hub rotation) while performing a local relative motion (pitching).

- `cyclicPitchMotion`: A specific solver designed for rotorcraft where the pitch angle varies sinusoidally relative to the rotational azimuth.

- `alpha0`: Represents the Collective Pitch ($\theta_0$), the constant baseline angle of the blades.


- `amplitude` & `phase`: These parameters define the Cyclic Pitch, derived from the lateral and longitudinal control inputs to determine the tilt and direction of the rotor thrust.
