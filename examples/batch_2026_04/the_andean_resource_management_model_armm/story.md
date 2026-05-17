# Story: The Andean Resource Management Model (ARMM)

## Research Motivation

ARMM is a theoretical agent-based model that formalizes Murra's Theory of Verticality (Murra, 1972) to explore how multi-zonal resource management systems emerge in mountain landscapes. The model identifies the social, political, and economic mechanisms that enable vertical complementarity across ecological gradients.
Built in NetLogo, ARMM employs an abstract 111×111 grid divided into four Andean ecological zones (Altiplano, Highland, Lowland, Coast), each containing up to 18 resource types distributed according to ecological suitability. To test general theoretical principles rather than replicate specific geography, resource locations are randomized at each model initialization.
Settlement agents pursue one of two economic strategies: diversification (seeking resource variety, maximum 2 units per type) or accumulation (maximising total quantity, maximum 30 units). Agents move between adjacent zones through hierarchical decision-making, first attempting peaceful interactions—coexistence (governed by tolerance) and trading (governed by cooperation)—before resorting to conflict (theft or takeover, governed by belligerence).
The model demonstrates that vertical complementarity can emerge through fundamentally different mechanisms: either through autonomous mobility under political decentralization or through state-coordinated redistribution under centralization. Sensitivity analysis reveals that belligerence and economic strategy explain approximately 25% of outcome variance, confirming that structural inequalities between zones result from political-economic organization rather than environmental constraints alone.
As a preliminary theoretical model, ARMM intentionally maintains simplicity to isolate core mechanisms and generate testable hypotheses. This foundational framework will guide future empirically-calibrated versions that incorporate specific archaeological settlement data and geographic features from the Carangas region (Bolivia-Chile border), enabling direct comparison between theoretical predictions and observed historical patterns.

## Research Goal

Replicate and extend the The Andean Resource Management Model (ARMM) model. Analyze emergent dynamics through parameter exploration and sensitivity analysis.

## Agent Description

Agent types and behavioral rules should be inferred from the model description above. Use the associated publication for detailed specifications if available.

## Parameters of Interest

To be determined from model specification.

## Output of Interest

Key aggregate metrics and time series as described in the research goal.

## Mode

Simulator

## Source

- **CoMSES URL**: https://www.comses.net/codebases/68a26f8a-08f5-473a-afe9-91740c037633/
- **Publication**: Murra, J. V. (1972). El control vertical de un máximo de pisos ecológicos en la economía de las sociedades andinas. In Visita de la Provincia de León de Huánuco en 1562, Iñigo Ortiz de Zúñiga, visitador (Vol. 2, pp. 429–476). Universidad Nacional Hermilio Valdizán.
- **Contributors**: Olga Palacios
- **Peer Reviewed**: Yes
