"use client";

// The one place GSAP and its plugins are registered. Loaded only through motion-lib.ts, after
// the landing page has loaded, and never by /workspace, /study or /results (AGENTS.md section 9).
import gsap from "gsap";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

gsap.registerPlugin(ScrollTrigger, SplitText, DrawSVGPlugin);

export { DrawSVGPlugin, gsap, ScrollTrigger, SplitText };
