# Oldhand Design QA

## Evidence

- Source visual truth: `design/option-2-reference.png`
- Source pixels: 809 × 1942
- Browser-rendered implementation: `implementation-desktop-stitched.png`
- Implementation pixels: 1440 × 5861
- Full-view comparison: `design-comparison-1.png`
- Focused comparison: `design-comparison-focused.png`
- Mobile capture: `implementation-mobile-top.png`
- Desktop CSS viewport: 1440 × 1000 at device pixel ratio 1
- Mobile CSS viewport: 390 × 844 at device pixel ratio 1
- State: unauthenticated public landing page; Claude install selected initially
- Density normalization: both full-page images were scaled to 2000 px high
  before the side-by-side comparison. Focused regions were independently scaled
  to 900 px wide.

## Findings

No actionable P0, P1, or P2 differences remain.

- Fonts and typography: Archivo Black, Archivo Narrow, and Space Mono reproduce
  the mock's compressed editorial headline, practical body copy, and technical
  labels. Hierarchy, wrapping, and optical weight remain clear at desktop and
  mobile widths.
- Spacing and layout rhythm: the page keeps the mock's work-order structure,
  thin rules, hard corners, generous section breaks, and alternating inspection
  panels. The mobile layout has no horizontal overflow at 390 px.
- Colors and visual tokens: warm ivory, near-black, safety orange, blueprint
  blue, and inspection green match the selected direction with accessible
  contrast and no decorative gradients.
- Image quality and asset fidelity: the generated inspection stamp and
  browser-proof capture are sharp, correctly cropped, and consistent with the
  mock. UI icons use the MIT-licensed Phosphor library rather than drawn
  substitutes.
- Copy and content: the pain points, adaptable inputs, Fable and GPT-5.6 Sol
  orchestration, browser proof, and two-command install match the selected
  concept and the repository's actual commands.

## Interaction Checks

- Claude and Codex install tabs switch to the correct two commands.
- Copy-to-clipboard returns the exact selected command and shows a `COPIED`
  confirmation.
- Source intake rows toggle and update the selected count.
- The primary Install Oldhand CTA scrolls to the final install section.
- Desktop and mobile layouts render without horizontal overflow.
- Browser console errors and warnings checked: none.

## Comparison History

- Initial full-page evidence was invalid because the browser's stitched capture
  repeated scroll positions. Removed the document-level smooth-scroll rule,
  retained smooth behavior on the primary CTA only, captured seven exact
  viewport segments, and stitched them at their measured scroll offsets.
- The first interaction pass exposed clipboard permission failure in the local
  browser. Added the native `execCommand("copy")` fallback and retested the
  exact command through the browser clipboard successfully.
- Post-fix full-view and focused comparisons show no actionable P0/P1/P2
  differences.

## Follow-up Polish

- P3: the implementation uses platform tabs instead of keeping both command
  columns visible at once. This is an intentional responsive interaction and
  preserves the two-command promise.
- P3: the source mock has heavier paper grain and handwritten blueprint marks.
  The implementation keeps a cleaner ivory surface for readability.

## Final Result

final result: passed
