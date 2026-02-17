# 2D Oscillating NACA 0012 Airfoil Simulation

The flow field surrounding an oscillating airfoil in deep stall is characterized by significant flow separation and the periodic shedding of dynamic stall vortices [1] [2].

[![Video Title](https://img.youtube.com/vi/Fds-anIRUr8/0.jpg)](https://www.youtube.com/watch?v=Fds-anIRUr8)

## Flow Conditions
 The simulation parameters are defined to capture unsteady aerodynamic effects at a high Reynolds number and moderate Mach number:

* **Mach Number:** $M_{\infty} = 0.283$
* **Reynolds Number:** $Re = 3.45 \times 10^6$
* **Angle of Attack:** $\alpha(t) = 15^\circ + 10^\circ \sin(\omega t)$  
* **Reduced Frequency ($k$)** = $0.151$ corresponding to an **Angular Velocity ($\omega$)** of $29.83 \text{ rad/s}$
---

## Numerical Setup (`pimpleFoam`)
The oscillating and rotating motion of the airfoil is modeled using the custom [`cyclicPitchMotion`](https://github.com/bosung-gotocloud/gotocfd/tree/main/cyclicPitchMotionSolver) solver for OpenFOAM. The transient simulation is performed using the `pimpleFoam` solver framework, which utilizes the PIMPLE algorithm for robust pressure-velocity coupling in unsteady flows.

* **Time Step ($\Delta t$):** $0.00107 \text{ s}$ (200 steps per oscillation period).
* **Duration:** 10 full oscillation periods to achieve a periodic steady state.
* **Mesh Resolution:** First cell height is $1 \times 10^{-4} \text{ m}$ to resolve the boundary layer.
* **Turbulence Model:** Spalart–Allmaras turbulence model

---

## Execution
To run the simulation in an **OpenFOAM-v2512** environment, Add the `cyclicPitchMotion` solver to OpenFOAM-v2512 according to the instruction in https://github.com/bosung-gotocloud/gotocfd/tree/main/cyclicPitchMotionSolver. And execute the following commands. The `decomposeParDict` is configured for 8 subdomains by default.

```bash
cd case
# Partition the mesh for parallel processing
decomposePar

# Execute the solver in parallel using MPI
mpirun -np 8 pimpleFoam -parallel
```


[1] W.J. McCroskey et al., "An Experimental Study of Dynamic Stall on Advanced Airfoil Sections," Vol. 1-3, NASA TM-84245, 1982


[2] Lee, B., Lee, S. and Lee, D. H., “Modification of SST Turbulence Model for Computation of Oscillating Airfoil Flows,“ Journal of computational fluids engineering, Vol. 4, No. 3, 1999, pp. 44~51.




