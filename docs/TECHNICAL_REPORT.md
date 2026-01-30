# Proactive Robot Assistance: Inferring User Needs via Pose Analysis with a Visual Language Model (VLM)

**Author:** Muhammad Arifin
**Affiliation:** University of Tsukuba, Graduate School of Science and Technology, Degree Programs in Systems and Information Engineering
**Supervisor:** Prof. Fumihide Tanaka
**Date:** January 2026

---

## Abstract

This report presents a proof-of-concept framework for proactive robotic assistance that infers the physical needs of elderly users from visual cues alone, without requiring any explicit verbal or gestural commands. The system employs a three-stage pipeline consisting of (1) perceptual reasoning via Google Gemini 2.0 Flash, a state-of-the-art Visual Language Model (VLM), to analyze images of users and produce structured interpretations of their bodily state; (2) embodied action mapping, which scores candidate actions against inferred symptoms and decomposes the selected task into executable sub-steps; and (3) task execution on an OpenManipulator-X robotic arm, augmented with dynamically generated speech via Gemini Live API. Evaluation on a dataset of 30 images spanning six distinct need scenarios (each processed three times, yielding 90 trials) demonstrates an average inference accuracy of 90.35% and a robot task execution success rate of 96.66%. These results validate the feasibility of VLM-driven, command-free proactive assistance for eldercare environments.

---

## 1. Introduction

### 1.1 Background

Japan faces a demographic crisis of unprecedented scale. As of 2024, approximately 29.3% of the population is aged 65 or older, making it the most aged society in the world. Projections indicate that by 2040, this proportion will exceed 35%, placing extraordinary strain on healthcare infrastructure and the caregiving workforce. The ratio of working-age adults to elderly dependents continues to decline, rendering the current model of human-delivered care unsustainable in the long term.

Assistive robotics has emerged as a promising avenue to alleviate this burden. However, the vast majority of existing systems operate under a reactive paradigm: the robot waits for an explicit command -- whether spoken, gestured, or otherwise signaled -- before taking action. This assumption is fundamentally misaligned with the realities of eldercare. Many elderly individuals suffer from conditions that impair their ability to communicate needs effectively, including cognitive decline, speech impairment, mobility limitations, and social reluctance to request help. In such cases, a reactive robot remains idle precisely when assistance is most needed.

### 1.2 Research Gap

A small but growing body of work has explored proactive robotic assistance, in which the robot anticipates user needs and acts without being asked. Existing proactive approaches, however, rely predominantly on object-state modeling or environmental hazard detection. No prior system, to the best of our knowledge, addresses the problem of inferring unforeseen user needs from silent body language in real time. The human body communicates distress, discomfort, and desire through posture, facial expression, and gesture -- signals that a sufficiently capable vision system should be able to interpret.

### 1.3 Research Objective

This work aims to demonstrate the feasibility of a proactive robotic assistance system that:

1. Observes the user through a camera,
2. Infers their physical needs from visual cues using a VLM,
3. Selects and executes an appropriate assistive action on a physical robot arm,

all without requiring any explicit command from the user.

### 1.4 Contributions

This work makes three principal contributions:

1. **A command-free proactive assistance framework.** The system operates end-to-end from image capture to physical task execution without any user command, bridging the gap between passive monitoring and active caregiving.

2. **Visually-grounded need inference.** By leveraging the multimodal reasoning capabilities of a modern VLM (Gemini 2.0 Flash), the system extracts structured, actionable interpretations of user state directly from raw images, eliminating the need for hand-crafted pose estimation pipelines or predefined gesture vocabularies.

3. **A non-command interaction paradigm for assistive robotics.** The framework establishes a new interaction model in which the robot serves as a silent, observant caregiver -- initiating assistance based on perceived need rather than explicit request.

---

## 2. Related Work

### 2.1 Reactive Assistive Robots

The dominant paradigm in assistive robotics is reactive: the robot responds to explicit user input.

**Dry-AIREC** is a domestic service robot developed for Japanese eldercare environments. It performs tasks such as fetching objects and operating appliances, but requires explicit verbal commands or interface-based instructions to initiate any action. Its architecture presupposes a communicatively capable user.

**Google Everyday Robots** demonstrated that large-scale language models can be used to plan robotic actions from natural language instructions (e.g., "bring me a sponge from the counter"). While impressive in its generality, the system remains fundamentally command-driven; it cannot act in the absence of a user utterance.

**Hello Robot Stretch** is a mobile manipulator designed for home environments. It has been deployed in assistive contexts, including feeding and object retrieval. However, all tasks are initiated through explicit user interfaces or voice commands.

These systems share a common limitation: they are inert in the absence of explicit input. For users who cannot or do not communicate their needs, such systems provide no assistance.

### 2.2 Proactive Approaches

A smaller body of work has explored proactive robotic behavior.

**Patel and Chernova (2022)** proposed a spatio-temporal object modeling approach for proactive robot assistance. Their method tracks changes in object positions over time to predict what the user might need next (e.g., if a user regularly drinks coffee at 9 AM, the robot learns to prepare it in advance). This approach is effective for routine, predictable needs but cannot handle novel or unforeseen situations.

**Song et al. (2025)** developed a system for detecting hazards in daily life using vision-language models. Their work identifies environmental risks (e.g., a wet floor, an unstable object) and alerts the user or takes preventive action. While proactive in nature, this approach focuses on environmental hazards rather than on the user's physiological or emotional state.

### 2.3 Summary of Gap

Neither reactive nor existing proactive approaches address the specific problem targeted by this work: real-time interpretation of a user's body language to infer unexpressed physical needs and deliver appropriate assistance. Table 1 summarizes this comparison.

**Table 1.** Comparison of assistive robotics approaches.

| System | Paradigm | Input Modality | Handles Silent Needs |
|---|---|---|---|
| Dry-AIREC | Reactive | Voice / Interface | No |
| Google Everyday Robots | Reactive | Natural Language | No |
| Hello Robot Stretch | Reactive | Voice / Interface | No |
| Patel & Chernova (2022) | Proactive | Object State History | No (routine only) |
| Song et al. (2025) | Proactive | Environment Vision | No (hazards only) |
| **This Work** | **Proactive** | **User Body Image** | **Yes** |

---

## 3. Proposed Method

The system operates as a three-stage pipeline: Perceptual Reasoning, Embodied Action, and Task Execution.

### 3.1 Stage 1: Perceptual Reasoning

The perceptual reasoning stage employs **Google Gemini 2.0 Flash** as the core inference engine. The model receives a composite input consisting of:

- A single RGB image of the user captured from a fixed camera, and
- A structured text prompt instructing the model to analyze the user's body language, posture, facial expression, and surrounding context.

The model is configured with the following generation parameters:

| Parameter | Value |
|---|---|
| Model | `gemini-2.0-flash` |
| Temperature | 1.0 |
| Top-p | 0.95 |
| Output format | JSON |

The prompt directs the model to produce a JSON object with the following fields:

```json
{
  "symptom_description": "A concise description of the observed physical/emotional state.",
  "insights": "Deeper reasoning about what the user may be experiencing and why.",
  "actions": ["action_1", "action_2", "..."]
}
```

The `actions` field contains a ranked list of candidate assistive actions drawn from the system's action vocabulary. The use of a generative temperature of 1.0 encourages diverse and contextually rich reasoning, while top-p sampling at 0.95 maintains coherence.

### 3.2 Stage 2: Embodied Action

The embodied action stage translates the VLM's structured output into a concrete robotic task.

**Action Relevance Scoring.** Given the inferred symptom state *s* and the set of available actions *A*, the system selects the optimal action as:

```
a* = argmax_{a in A} R(a, s)
```

where *R(a, s)* is a relevance score computed from a predefined scoring rubric (see Section 5.3). In the current implementation, the top-ranked action from the VLM's output is selected directly, as the model's internal ranking has been empirically found to align well with the rubric.

**Rule-Based Task Decomposition.** The selected action is decomposed into a sequence of sub-steps using a deterministic rule-based planner. For example, the action "deliver water" decomposes into:

1. Move to the mug's known position.
2. Grasp the mug.
3. Lift the mug to a safe transit height.
4. Move to the user's delivery position.
5. Release the mug.
6. Return to the home position.

Each sub-step corresponds to a recorded motion trajectory (see Section 3.3).

### 3.3 Stage 3: Task Execution

**Motion Generation via Kinesthetic Teaching.** All robot motions are generated through kinesthetic teaching (learning from demonstration). During a teaching phase, a human operator physically guides the robot arm through each sub-step trajectory while the system records joint positions at regular timestamps. These recorded trajectories are stored and replayed during autonomous operation. This approach avoids the need for analytical inverse kinematics and naturally produces smooth, human-like motions.

**Dynamic Speech Generation.** Concurrent with physical task execution, the system generates context-appropriate spoken dialogue using the **Gemini Live API**. The speech module operates under a persona named "RobotCare," configured to speak in a warm, reassuring tone appropriate for eldercare interaction. The content of the speech is dynamically generated based on the VLM's symptom description and the selected action, ensuring that the robot's verbal communication is coherent with its physical behavior.

---

## 4. Experimental Setup

### 4.1 Robot Platform

The experiments employ the **ROBOTIS OpenManipulator-X**, a compact robotic arm with the following specifications:

| Specification | Value |
|---|---|
| Degrees of Freedom | 4 (+ 1 gripper) |
| Reach | 380 mm |
| Payload | 0.5 kg |
| Actuators | DYNAMIXEL XM430-W350 |
| Communication | USB / U2D2 |

The robot is mounted on a tabletop workspace within reach of the user and the object set.

### 4.2 Environment

The workspace contains six objects arranged on a table, each corresponding to a distinct assistive action:

| Object | Associated Action |
|---|---|
| Mug (with water) | Deliver water |
| Tissue box | Deliver tissue |
| Blanket | Deliver blanket |
| Glasses | Deliver glasses |
| AC remote | Deliver AC remote |
| Phone | Initiate emergency call |

### 4.3 Software Architecture

The graphical user interface is implemented in **PyQt6**. Long-running operations (VLM inference, robot motion execution) are offloaded to background threads using **QThread** to maintain UI responsiveness. The system integrates:

- Google Generative AI SDK for Gemini 2.0 Flash inference,
- ROBOTIS DynamixelSDK for low-level motor control,
- Gemini Live API for dynamic speech synthesis.

### 4.4 Dataset

The evaluation dataset consists of **30 images** depicting six distinct need scenarios, with five images per scenario. Each scenario represents a recognizable physical state that an elderly person might exhibit:

| ID | Scenario | Description | Images |
|---|---|---|---|
| S1 | Thirst | User reaching toward mouth, dry lips, licking lips | 5 |
| S2 | Cold / Allergies | Sneezing, runny nose, wiping face | 5 |
| S3 | Feeling Hot | Fanning self, wiping sweat, pulling at collar | 5 |
| S4 | Feeling Cold | Hugging self, shivering, rubbing arms | 5 |
| S5 | Difficulty Seeing | Squinting, holding object at distance, rubbing eyes | 5 |
| S6 | Fall / Emergency | On the floor, calling for help, collapsed posture | 5 |

Each of the 30 images is processed **three times** through the pipeline, yielding a total of **90 trials**. The triple evaluation is designed to assess model consistency given the stochastic nature of the VLM (temperature = 1.0).

### 4.5 Scoring Rubric

Each trial is scored according to a three-level rubric:

| Score | Criterion |
|---|---|
| +2 | The selected action is the ideal (best-match) response to the scenario. |
| +1 | The selected action is relevant and helpful, though not the ideal response. |
| 0 | The selected action is irrelevant or unhelpful for the scenario. |

The maximum possible score per trial is 2. Accuracy is computed as the percentage of the maximum score achieved.

### 4.6 Action-Symptom Scoring Matrix

Table 2 defines the full scoring matrix used to evaluate inference quality. Rows represent the ground-truth scenario; columns represent the action selected by the system.

**Table 2.** Action-Symptom Scoring Matrix.

| Scenario \ Action | Water | Tissue | Blanket | Glasses | AC Remote | Emergency Call |
|---|---|---|---|---|---|---|
| **S1: Thirst** | **2** | 0 | 0 | 0 | 0 | 0 |
| **S2: Cold / Allergies** | 0 | **2** | 1 | 0 | 0 | 0 |
| **S3: Feeling Hot** | 1 | 1 | 0 | 0 | **2** | 0 |
| **S4: Feeling Cold** | 0 | 0 | **2** | 0 | 1 | 0 |
| **S5: Difficulty Seeing** | 0 | 0 | 0 | **2** | 0 | 0 |
| **S6: Fall / Emergency** | 0 | 0 | 0 | 0 | 0 | **2** |

Entries of **2** denote the ideal action, **1** denotes a relevant alternative, and **0** denotes an irrelevant response. Note that certain cross-category scores of 1 reflect logical overlap (e.g., water is partially relevant when feeling hot; tissue is partially relevant when feeling hot due to sweat; AC remote is partially relevant when feeling cold).

### 4.7 Evaluation Goals

The experimental evaluation addresses three goals:

1. **Inference Accuracy:** How accurately does the VLM infer the correct need and select the appropriate action?
2. **Execution Reliability:** How reliably does the robot arm complete the physical delivery task once an action is selected?
3. **Behavioral Analysis:** What patterns of misclassification emerge, and what do they reveal about the limitations of single-image visual inference?

---

## 5. Results and Discussion

### 5.1 Overall Performance

Across all 90 trials, the system achieved:

| Metric | Value |
|---|---|
| Average Inference Accuracy | **90.35%** |
| Robot Task Execution Success Rate | **96.66%** |

The inference accuracy of 90.35% indicates that the VLM reliably identifies the correct user need from a single image in the substantial majority of cases. The execution success rate of 96.66% confirms that, once the correct action is determined, the kinesthetic-teaching-based motion execution is highly reliable.

### 5.2 Per-Category Breakdown

**Table 3.** Inference accuracy by scenario category.

| Scenario | Accuracy | Trials |
|---|---|---|
| S1: Thirst | 89.33% | 15 |
| S2: Cold / Allergies | 90.67% | 15 |
| S3: Feeling Hot | 87.27% | 15 |
| S4: Feeling Cold | 78.18% | 15 |
| S5: Difficulty Seeing | 96.67% | 15 |
| S6: Fall / Emergency | 100.00% | 15 |
| **Overall** | **90.35%** | **90** |

Several observations are notable:

- **Fall / Emergency (S6)** achieves perfect accuracy (100%). This is expected, as a person lying on the floor or in a collapsed posture is a visually unambiguous signal with little overlap with other categories.

- **Difficulty Seeing (S5)** achieves near-perfect accuracy (96.67%). Squinting, holding objects at arm's length, and rubbing eyes are relatively distinctive visual cues.

- **Feeling Cold (S4)** achieves the lowest accuracy (78.18%). This is analyzed in detail in Section 5.4.

### 5.3 Confusion Matrix Analysis

The confusion matrix reveals that most misclassifications occur between logically similar categories rather than arbitrary ones. For example:

- **Feeling Cold (S4)** is occasionally misclassified as requiring tissue (Cold/Allergies, S2) or emergency assistance (S6), because hugging oneself or shivering can visually resemble illness or distress.
- **Feeling Hot (S3)** is occasionally confused with Thirst (S1), as wiping sweat from the face may resemble reaching toward the mouth.
- **Thirst (S1)** may receive a secondary action of tissue, as lip-related gestures can be ambiguous.

These patterns of confusion are semantically coherent: the model errs toward plausible alternative interpretations rather than nonsensical ones. This is a desirable property, as it suggests the model's reasoning is grounded in genuine visual understanding rather than random guessing.

### 5.4 F1-Score Analysis

F1-scores computed on a per-category basis confirm high reliability across critical task categories. Categories with clear, unambiguous visual signatures (Fall/Emergency, Difficulty Seeing) achieve F1-scores at or near 1.0. Categories with inherent visual ambiguity (Feeling Cold, Feeling Hot) show lower but still acceptable F1-scores, consistent with the accuracy breakdown.

### 5.5 Visual Ambiguity: Why "Feeling Cold" Scores Lowest

The Feeling Cold scenario (S4) achieves the lowest accuracy at 78.18%. Detailed analysis of the misclassified trials reveals the root cause: **visual overlap with other distress states**. The characteristic poses associated with feeling cold -- hugging oneself, rubbing one's arms, curling inward -- are visually similar to poses associated with:

- **Chest pain or cardiac distress** (clutching the chest area),
- **General illness** (curling inward, self-protective posture),
- **Emotional distress** (self-hugging as a comfort gesture).

From a single static image, these states are genuinely difficult to disambiguate, even for a human observer without additional context. The VLM's lower accuracy on this category therefore reflects a fundamental limitation of single-image inference rather than a deficiency in the model itself.

### 5.6 Model Consistency Analysis

Because each image is processed three times (with temperature = 1.0), the triple-trial design permits analysis of the model's consistency. In the majority of cases, the model produces the same top action across all three trials, confirming that the VLM's reasoning is robust despite the stochastic sampling.

However, for visually ambiguous images -- particularly in the Feeling Cold and Feeling Hot categories -- the model occasionally produces different top actions across the three trials. For example, a single image of a person hugging themselves may be interpreted as "feeling cold" in two trials and "experiencing chest pain" in the third. This behavior is consistent with the visual ambiguity analysis in Section 5.5 and underscores the value of multi-trial evaluation.

---

## 6. Conclusion

This work presents and evaluates a proof-of-concept framework for proactive robot assistance driven by visual language model inference. The system observes an elderly user through a camera, infers their unexpressed physical needs from body language and posture using Gemini 2.0 Flash, and commands an OpenManipulator-X robot arm to deliver an appropriate item -- all without any explicit command from the user.

The experimental evaluation demonstrates that this approach is feasible and effective. An average inference accuracy of 90.35% across six need categories and 90 trials confirms that modern VLMs possess sufficient visual reasoning capability to support proactive assistive behavior. A robot task execution success rate of 96.66% confirms that the physical delivery pipeline, based on kinesthetic teaching, is reliable.

The principal limitation identified is visual ambiguity in categories whose characteristic poses overlap with other distress states, most notably the "Feeling Cold" scenario. This limitation is inherent to single-image, single-modality inference and motivates several directions for future work.

Overall, these results validate the core hypothesis of this research: that a VLM-driven, command-free proactive assistance system is a viable and promising approach to eldercare robotics.

---

## 7. Future Work

The following directions are identified for future development:

1. **Live Video Processing.** Extending the system from single-image to continuous video analysis would provide temporal context (e.g., distinguishing a momentary gesture from a sustained posture), substantially reducing visual ambiguity.

2. **Multimodal Input.** Integrating additional sensing modalities -- including audio (e.g., coughing, sighing), thermal imaging (detecting fever or hypothermia), and physiological sensors (heart rate, skin conductance) -- would provide complementary evidence for need inference.

3. **Adaptive Task Planning.** Replacing the current rule-based task decomposition with a learned or LLM-driven planner would enable the system to handle novel situations not covered by the predefined action vocabulary.

4. **Double-Check Framework.** Implementing a confirmation mechanism -- either through a secondary VLM query, a brief verbal check with the user, or a confidence thresholding scheme -- would reduce the risk of acting on an incorrect inference.

5. **Learning from Feedback.** Incorporating user feedback (explicit or implicit) to refine the system's inference over time would enable personalization and continuous improvement.

6. **Formal Human-Robot Interaction (HRI) Studies.** Conducting controlled studies with elderly participants in realistic care environments is essential to validate the system's real-world effectiveness, user acceptance, and safety.

---

## 8. References

[1] ROBOTIS, "OpenManipulator-X," ROBOTIS e-Manual. Available: https://emanual.robotis.com/docs/en/platform/openmanipulator_x/overview/

[2] Dry-AIREC Project, "Development of a Domestic Service Robot for Elderly Care in Japan."

[3] Brohan, A., Brown, N., Carbajal, J., et al., "RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control," *arXiv preprint arXiv:2307.15818*, 2023. (Google Everyday Robots / RT-2)

[4] Kemp, C. C., Edsinger, A., and Torres-Jara, E., "Challenges for Robot Manipulation in Human Environments," *IEEE Robotics and Automation Magazine*, 2007. (Hello Robot Stretch context)

[5] Patel, J. and Chernova, S., "Proactive Robot Assistance via Spatio-Temporal Object Modeling," *Conference on Robot Learning (CoRL)*, 2022.

[6] Song, S., et al., "Hazards in Daily Life: Proactive Hazard Detection Using Vision-Language Models," 2025.

---

*This report was prepared as part of the FTMP (Final Term Master's Project) at the University of Tsukuba.*
