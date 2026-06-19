# BMAD Project Brief: Comfort Factors MVP

**Role:** Analyst
**Project Name:** Comfort Factors
**Status:** Draft

## 1. Problem Statement
Existing walkability and bikeability indices (like Walk Score) primarily rely on proximity data—how close a person is to a destination. However, this fails to account for the **human experience** of moving through a space. Factors like extreme heat, high noise levels, lack of shade, or poor air quality can deter active transit even if the distance is short, forcing individuals to choose cars.

## 2. Target Audience
- **Local Governments (Urban Planners):** To identify environmental stressors that deter active transit and prioritize infrastructure investments (e.g., tree canopies, noise mitigation).
- **Real Estate & Urban Developers:** To assess the "comfort value" of potential sites and justify pedestrian-oriented design choices to stakeholders and residents.

## 3. High-Level Goals
- **MVP Capability:** Allow any city in the United States to generate an active transit map based on "comfort factors."
- **Data Integration:** Incorporate environmental variables (Heat, Noise, Shade, etc.) alongside traditional proximity data.
- **Encouragement of Development:** Provide actionable insights that lead to more pedestrian-friendly urban design.

## 4. Proposed Comfort Factors (Variables)
- **Thermal Comfort:** Surface temperature, urban heat island intensity, shade availability.
- **Acoustic Comfort:** Proximity to highways, industrial noise levels, traffic volume.
- **Air Quality:** PM2.5 levels, proximity to high-traffic corridors.
- **Safety & Aesthetics:** Sidewalk width, presence of greenery, street lighting (optional for MVP).

## 5. Data Strategy: Simulation & Existing Public Sensors
*Critical Constraint based on previous learnings:* The project will **strictly avoid** the deployment of *new* physical IoT sensors. Deploying proprietary hardware introduces immense regulatory hurdles and destroys the ability to scale nationally.

Instead, the MVP relies on a hybrid approach:
1. **Simulated and Inferred Data:** For scalable baseline metrics across all US cities.
    - **OSM (OpenStreetMap):** Base transit networks, building footprints (for shade simulation).
    - **NOAA/NASA:** Satellite-derived temperature and Urban Heat Island (UHI) proxies.
    - **US DOT National Transportation Noise Map:** For acoustic stress.
2. **Existing Public Sensor Networks (Calibration):** To "harden" and validate the simulations, the system will reference publicly available, pre-existing sensor data where available.
    - Examples: Municipal weather stations, PurpleAir networks (for air quality/temperature), or existing DOT noise monitors.
    - *Purpose:* This ground-truth data is used to calibrate the simulation models, ensuring the inferred data accurately reflects real-world conditions without the burden of deploying our own hardware.

## 6. MVP Scope
- Initial focus on 2-3 key comfort factors (e.g., Heat and Noise).
- Web-based map visualization for a selected city or a scalable framework for any US city.
- Basic scoring system: "Comfort Score" vs. "Proximity Score."
