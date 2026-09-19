---
trigger: always_on
description: UI/UX design vocabulary and interaction checklist (Structure vs Interaction vs Polish).
---

# UI/UX Design — Structure vs Interaction vs Polish

**Core Invariant:** Structure decides _where_ things live and in what order. Interaction design decides _how the product behaves while you use it_ (especially while it is busy). Visual polish decides _how it looks_. Structure precedes interaction; interaction precedes polish. Never apply visual polish to mask a broken interaction or broken structure.

---

## 1. The three words, precisely

| Term                     | What it means                                                                                 | Question it answers                                                            |
| ------------------------ | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| **UX (User Experience)** | The whole experience of using the product — flow, logic, ease, frustration, waiting, recovery | "Can the user complete the task, and how does it feel end-to-end?"             |
| **UI (User Interface)**  | The concrete visual + interactive surface — screens, buttons, text, motion                    | "What exactly does the user see and touch?"                                    |
| **Interaction design**   | How the interface _behaves_ over time — streaming, scrolling, loading, cancel, approve, undo  | "What happens while the user is mid-task, especially when the system is busy?" |

**UX is upstream of UI.** You design the experience and flows first, then build screens to express them.

**Interaction design sits between structure and visual polish.** A beautiful chat that yanks the scrollbar while tokens stream has good polish and broken interaction.

---

## 2. The Structure layer — "where does this button go"

This is **information architecture**: organizing content and actions so people can find and do things without hunting.

| Term                            | Meaning                                                                                                                                            |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Information architecture**    | The map of the product: what screens exist, how they relate, and where each control lives                                                          |
| **Operator jobs**               | The real tasks a person is trying to finish (start a chat, approve a dangerous action, open a finished job) — not the feature names on the buttons |
| **User flow / user journey**    | The ordered path to complete a goal (e.g., ask → job runs → approve → done)                                                                        |
| **Wireframe**                   | Low-fidelity sketch of a screen — boxes and labels, no colors. Structure only                                                                      |
| **Hierarchy**                   | What matters most gets the most attention: biggest, first, top-left (or top of the scan path)                                                      |
| **Layout / grid**               | The invisible skeleton that aligns everything: columns, rows, gutters                                                                              |
| **Whitespace (negative space)** | Deliberate empty space that separates and groups — a structural tool, not "wasted" space                                                           |
| **Primary vs secondary action** | One dominant action per screen or panel (the big button); everything else is quieter                                                               |
| **Navigation patterns**         | Tabs, sidebars, breadcrumbs, window docks — the "roads" of the product                                                                             |
| **Wayfinding**                  | Always knowing where you are and how to get back                                                                                                   |
| **Progressive disclosure**      | Show only what is needed now; reveal the rest when asked                                                                                           |
| **Mental model**                | The user's picture of how the product works; good design matches it                                                                                |
| **Duplicate controls**          | Two different UI pieces that do the same operator job (e.g., two agent pickers) — a structure failure                                              |

**Structure test:** Can a user complete the core task with labels stripped and colors removed? If not, the structure is broken — no amount of polish fixes it.

---

## 3. The Interaction layer — "what happens while I use it"

This is the layer that catches gaps like "I cannot scroll while the chat is streaming." It is **not** information architecture and **not** corner polish.

| Term                                         | Meaning                                                                                                                    |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Interaction pattern**                      | A named, reusable behavior (smart autoscroll, sticky header, confirm-before-destroy)                                       |
| **Affordance**                               | A cue that something _can_ be used a certain way (a button looks pressable)                                                |
| **Signifier**                                | The explicit label or icon that tells you what it does ("Jump to latest")                                                  |
| **Discoverability**                          | Can you find the common action without hunting? (New Chat should not hide behind a nested window)                          |
| **System status**                            | The product always shows what it is doing: idle, thinking, streaming, waiting for you, done, failed                        |
| **Progress honesty**                         | Status matches reality — never "Done" while tokens or job phases are still running                                         |
| **Interruptibility**                         | During a long run you can still read, scroll, cancel, or approve without the UI fighting you                               |
| **Smart autoscroll (sticky follow-tail)**    | Auto-stick to new content only while you are at the bottom; if you scroll up, freeze and offer **Jump to latest**          |
| **Loading / empty / error / success states** | Every important surface has a clear look for waiting, nothing-here-yet, failure, and success                               |
| **Recovery**                                 | If something fails or you leave mid-stream, you can get back to the same job cleanly                                       |
| **Feedback**                                 | Every meaningful action gets a visible response (click, submit, approve, copy)                                             |
| **Cognitive load**                           | How much the user must hold in their head; fewer competing signals = lower load                                            |
| **Signal hierarchy**                         | Separate ambient state (a status dot) from actionable counts (a badge that needs a click) — do not stack both on every row |
| **Destructive confirmation**                 | Hard-to-undo actions ask clearly before they run                                                                           |
| **Human-in-the-loop surfacing**              | Approvals appear where the work started, with enough context to decide                                                     |

**Interaction test:** While the system is busy (streaming, long job, waiting for approval), can you still do the natural next human actions without the UI yanking you, lying about status, or hiding the common control?

---

## 4. Standing checklist (reuse on any studio or future app)

Use this **before** colors, corners, or spacing polish:

1. **Operator jobs** — What are you trying to do here? Is there more than one control for the same job?
2. **Waiting / streaming** — Can you still read, scroll, cancel, or approve without the UI yanking you?
3. **Progress honesty** — Does the screen tell the truth about running / done / failed?
4. **Discoverability** — Is the common action (New Chat, Jump to latest, Approve) obvious without hunting?
5. **Recovery** — If something goes wrong or you leave mid-stream, can you get back cleanly?

### Extra checks in the same spirit

1. **One primary action** — Is there a clear main next step, or are equal-looking buttons competing?
2. **Wayfinding** — Do you always know which studio, agent, session, and job you are in?
3. **Interruptibility** — Can a long run be paused, cancelled, or approved without losing place?
4. **Empty and error states** — Does "nothing here" or "this failed" explain what to do next?
5. **Duplicate levers** — Did the same job get two entry points that behave differently?
6. **Signal vs noise** — Are badges only for things that need action, not every ambient state?
7. **Mobile / narrow pane** — Does the layout still work when the window is small (two-line rows, no horizontal table overflow)?

**Done bar example (smart autoscroll):** While a chat job is streaming, you can scroll up freely; a **Jump to latest** control appears; it does not yank you down until you click it.

---

## 5. The Polish layer — "make corners soft, spaced by measurement"

Visual design applied **on top of** working structure and interaction.

| Term                              | Meaning                                                                                                          |
| --------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Visual design / art direction** | Color, typography, imagery — the "look"                                                                          |
| **Typography**                    | Font choice, size, weight, line-height — text as a design material                                               |
| **Color system**                  | A palette with roles: primary, neutral, success / warning / error                                                |
| **Spacing scale**                 | Measured, consistent spacing (e.g., 4pt or 8pt grid) — "spaced by measurement," not by eye                       |
| **Corner radius**                 | How rounded an edge is; small consistent values read as intentional style                                        |
| **Concentric radius**             | Nested rounded boxes share a geometric center: outer radius ≈ inner radius + padding                             |
| **Elevation / shadow**            | Layering: what floats above what (cards, modals)                                                                 |
| **Visual states**                 | Hover, focus, active, disabled, loading — how it _looks_ in each state (behavior of those states is interaction) |
| **Microinteraction / motion**     | Small animations that confirm actions (press, panel slide) — polish on top of a correct interaction              |
| **Design tokens**                 | Named values for color / spacing / radius so the whole product stays consistent                                  |
| **Design system**                 | The library of tokens + components that keeps polish consistent at scale                                         |

**Polish test:** Does it look intentional and consistent — or like a pile of small decisions made by eye?

---

## 6. The core distinction (three columns)

|                    | **Structure**                                   | **Interaction**                                                  | **Polish**                                     |
| ------------------ | ----------------------------------------------- | ---------------------------------------------------------------- | ---------------------------------------------- |
| **Decides**        | What exists, where, in what order               | How it behaves while you use it                                  | How it looks                                   |
| **Artifacts**      | Information architecture map, flows, wireframes | Pattern list, state diagrams, Done bars you can feel             | Style guide, tokens, components                |
| **Failure mode**   | Lost, two buttons for one job, can't finish     | Scroll fight, fake Done, can't cancel, can't find Jump to latest | Looks cheap, inconsistent, untrustworthy       |
| **Fixable later?** | Expensive to restructure                        | Medium — fixable but needs real behavior tests                   | Cheap to reskin                                |
| **Thinking type**  | "Where does this button go?"                    | "What happens while it is busy?"                                 | "Make the corners soft, spaced by measurement" |

**Rule of thumb:** You can polish a broken layout, and you can skin a hostile interaction — neither makes the product usable.  
**Order of work:** information architecture → flows → wireframes → **interaction patterns** → visual design → motion.

Skipping straight to "make it pretty" is how you get a beautiful product nobody can use.

---

## 7. Diagnostic Gate

When auditing or designing any studio interface, diagnose the layer before touching code:

1. **Structure issue?** (Missing action, duplicate levers, confusing layout) → Fix the information architecture and layout grid first.
2. **Interaction issue?** (Scroll yanked during streaming, fake "Done" while busy, missing cancel/resume, unresponsive controls) → Implement the missing interaction pattern (smart autoscroll, interruptibility, progress honesty).
3. **Polish issue?** (Spacing, radius, contrast, colors) → Apply measured design tokens only after structure and interaction are verified.

**Rule of Thumb:** Never polish a broken layout, and never skin a hostile interaction. Ensure the operator job feels right before styling corners.
