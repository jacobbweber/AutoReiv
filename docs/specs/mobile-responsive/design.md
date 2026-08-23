# Technical Design Specification: Mobile-First Responsive Layout & Viewport Overhaul

> **Document ID**: `DESIGN-RESP-001`  
> **Status**: Approved  
> **Traceability ID**: `[REQ-RESP-001]`, `[REQ-RESP-002]`, `[REQ-RESP-003]`

---

## 1. Responsive Viewport Architecture

```mermaid
flowchart TD
    subgraph Viewport ["Root Container (100dvh Dynamic Viewport)"]
        Header["Mobile Header (md:hidden) [☰ Menu] [AutoReiv]"]
        MainBody["Flex Content Area (h-full overflow-hidden)"]
    end

    subgraph ChatView ["Chat Studio (#view-chat)"]
        ChatHead["Top Agent Bar (flex-shrink-0)"]
        Messages["Message Stream (flex-1 overflow-y-auto)"]
        ChatBar["Sticky Prompt Bar (flex-shrink-0 sticky bottom-0)"]
    end

    subgraph WikiView ["Wiki Studio (#view-wiki)"]
        WikiHead["Wiki Top Bar (flex-shrink-0) [📁 Vault Drawer] [New Note]"]
        WikiDrawer["Off-Canvas Vault Tree (hidden md:flex md:w-80 absolute md:relative z-30)"]
        WikiDoc["Document Reader & Editor (flex-1 w-full overflow-y-auto)"]
    end

    MainBody --> ChatView
    MainBody --> WikiView
    ChatView --> ChatHead --> Messages --> ChatBar
    WikiView --> WikiHead --> WikiDrawer
    WikiView --> WikiDoc
```

---

## 2. Breakpoint Strategies (Tailwind CSS)

| Screen Size | Breakpoint | Navigation | Sidebars (Wiki / Docs) | Modals |
| :--- | :--- | :--- | :--- | :--- |
| **Mobile** | `< 768px` | Slide-over Hamburger Drawer | Slide-over Off-canvas Drawer | Fixed Fullscreen / 95vw Sheet |
| **Desktop** | `≥ 768px` | Fixed Left Sidebar (`w-72`) | Fixed Split-Pane Sidebar (`w-80`) | Centered Modal Dialog |
