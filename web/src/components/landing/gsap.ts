"use client";

// The one place GSAP and its plugins are registered. Imported only by components under
// components/landing, which only the / route uses (AGENTS.md section 9).
import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { DrawSVGPlugin } from "gsap/DrawSVGPlugin";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";

gsap.registerPlugin(useGSAP, ScrollTrigger, SplitText, DrawSVGPlugin);

export { DrawSVGPlugin, gsap, ScrollTrigger, SplitText, useGSAP };
