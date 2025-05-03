document.addEventListener('DOMContentLoaded', () => {
    const startButton = document.getElementById('startAnimationBtn');
    const diagram = document.getElementById('architectureDiagram');
    if (!startButton || !diagram) {
        console.error("Initialization failed: Button or Diagram SVG not found.");
        return;
    }

    // Get component *rectangles* directly for highlighting
    const userRect = document.getElementById('user');
    const orchestratorRect = document.getElementById('orchestrator');
    const financialRect = document.getElementById('financial-agent');
    const sentimentRect = document.getElementById('sentiment-agent');
    const mcpDbRect = document.getElementById('mcp-db');
    const mcpCryptoRect = document.getElementById('mcp-crypto');
    const mcpRedditRect = document.getElementById('mcp-reddit');

    const allLinks = diagram.querySelectorAll('.link');

    // --- Helper Functions ---
    function highlightElement(element, duration = 1000) {
        if (!element) {
            console.warn("Attempted to highlight a null element.");
            return;
        }
        element.classList.add('highlight');
        setTimeout(() => {
           element.classList.remove('highlight');
        }, duration);
    }

    function animateLink(linkId, duration = 1000) {
        const link = document.getElementById(linkId);
        if (!link) {
            console.warn(`Link with ID "${linkId}" not found.`);
            return;
        }
        // Reset offset just before activating if needed (usually handled by reset)
        // link.style.strokeDashoffset = '1000'; // Re-hide before animating if glitchy
        link.classList.add('active');
        // Remove class slightly after animation duration to ensure it completes
        setTimeout(() => {
             link.classList.remove('active');
        }, duration + 100); // Give it a little buffer
    }

    function resetAnimation() {
         console.log("Resetting animation...");
         // Remove highlights
        diagram.querySelectorAll('.highlight').forEach(el => el.classList.remove('highlight'));

        // Reset all links: remove 'active' and explicitly reset dashoffset
        allLinks.forEach(link => {
            link.classList.remove('active');
            // Crucial: Reset the dashoffset to hide the line again
            link.style.strokeDashoffset = '1000';
            // Force reflow might be needed in rare cases, but try without first
            // void link.offsetWidth;
        });
         // Allow a brief moment for reset styles to apply before starting new animation
         return new Promise(resolve => setTimeout(resolve, 50));
    }


    // --- Main Animation Sequence ---
    async function animateFlow() {
        startButton.disabled = true; // Prevent multiple clicks
        await resetAnimation(); // Wait for reset to complete
        console.log("Starting animation sequence...");

        let delay = 50; // Start shortly after reset
        const stepDuration = 1300; // Time between start of steps (animation time + pause)
        const highlightDuration = 1100; // How long components stay highlighted

        try {
            // 1. User -> Orchestrator
            setTimeout(() => {
                console.log("Step 1: User -> Orchestrator");
                highlightElement(userRect, highlightDuration);
                animateLink('link-user-orch', 1000);
            }, delay);
            delay += stepDuration;

            // 2. Orchestrator processes -> Financial
            setTimeout(() => {
                console.log("Step 2: Orchestrator -> Financial");
                highlightElement(orchestratorRect, highlightDuration);
                animateLink('link-orch-fin', 1000);
            }, delay);
            delay += stepDuration;

            // 3. Financial -> MCPs (DB & Crypto)
            setTimeout(() => {
                console.log("Step 3: Financial -> MCPs");
                highlightElement(financialRect, highlightDuration);
                animateLink('link-fin-db', 1000);
                animateLink('link-fin-crypto', 1000);
            }, delay);
            delay += stepDuration;

            // 4. MCPs -> Financial (Responses)
            setTimeout(() => {
                console.log("Step 4: MCPs -> Financial");
                highlightElement(mcpDbRect, highlightDuration);
                highlightElement(mcpCryptoRect, highlightDuration);
                animateLink('link-db-fin', 1000);
                animateLink('link-crypto-fin', 1000);
            }, delay);
            delay += stepDuration;

            // 5. Orchestrator -> Sentiment
            // (This might happen earlier/parallel in reality, sequential here for simplicity)
            setTimeout(() => {
                console.log("Step 5: Orchestrator -> Sentiment");
                highlightElement(orchestratorRect, highlightDuration); // Re-highlight briefly
                animateLink('link-orch-sent', 1000);
            }, delay);
            delay += stepDuration;

            // 6. Sentiment -> MCP Reddit
            setTimeout(() => {
                console.log("Step 6: Sentiment -> MCP Reddit");
                highlightElement(sentimentRect, highlightDuration);
                animateLink('link-sent-reddit', 1000);
            }, delay);
            delay += stepDuration;

            // 7. MCP Reddit -> Sentiment (Response)
            setTimeout(() => {
                console.log("Step 7: MCP Reddit -> Sentiment");
                highlightElement(mcpRedditRect, highlightDuration);
                animateLink('link-reddit-sent', 1000);
            }, delay);
            delay += stepDuration;

            // 8. Financial -> Orchestrator (Response)
            setTimeout(() => {
                 console.log("Step 8: Financial -> Orchestrator");
                 highlightElement(financialRect, highlightDuration); // Re-highlight briefly
                 animateLink('link-fin-orch', 1000);
            }, delay);
            delay += stepDuration;

            // 9. Sentiment -> Orchestrator (Response)
            setTimeout(() => {
                console.log("Step 9: Sentiment -> Orchestrator");
                highlightElement(sentimentRect, highlightDuration); // Re-highlight briefly
                animateLink('link-sent-orch', 1000);
            }, delay);
            delay += stepDuration;

             // 10. Orchestrator -> User (Final Response)
             setTimeout(() => {
                console.log("Step 10: Orchestrator -> User");
                highlightElement(orchestratorRect, highlightDuration); // Final highlight
                animateLink('link-orch-user', 1000);
             }, delay);
             delay += stepDuration;

             // 11. Highlight User receiving response & finish
             setTimeout(() => {
                 console.log("Step 11: User receives response");
                 highlightElement(userRect, highlightDuration);
                 console.log("Animation complete.");
                 startButton.disabled = false; // Re-enable button
             }, delay);

        } catch (error) {
            console.error("Error during animation sequence:", error);
            startButton.disabled = false; // Re-enable button on error
        }
    }

    startButton.addEventListener('click', animateFlow);
    console.log("Animation script loaded. Click button to start.");
});