# AI Prompts

Homework 6: Campus Customs Vendor Desk (Tokenomics + Prompt Injection). A log of what I typed to my vibe coder, one section per problem.

---

## Problem 1: Vibe Coder Prompts

**Prompt:**

> Prob #1-ok lets start hw6, it works the same way hw5 did. review my word doc HW6_Vendor_Desk_Agent.docx that has the assignmnet in my own words and i'll paste the screenshots so you can verfy the doc matches the live page. then set up the hw6/ folder and the AI_prompts.md log right at the start like we always do - one section per problem with the problem number and title and my prompt in my own words, plus a follow up if we needed one, and keep it updated as we go so by the end its a full record of how i described each problem to you. go one problem at a time, scope only.

**Follow-up:**

> use my PORTKEY_API_KEY and ONLY gpt-6-luna for evry AI call, not openai direct - my openai key ran out of credits so portkey is the one that works. note it in the readme.

*What was lacking after the first prompt: my first prompt didnt pin down which provider to use and my notes contradicted eachother (the old readme said openai direct, the newer note said openai was out of credits and portkey works), so i confirmed portkey + gpt-6-luna before anything called the model.*

---

## Problem 2: Size Up the Handbook

**Prompt:**

> Prob #2-lets size up the shop handbook before we build anything. look thru data/shop_handbook.md and data/prices.json - the handbook goes to the model on evry single call so i want to know what that costs. figure out how many tokens the handbook is and how you got the number, then work out what the handbook ALONE costs in dollars on one call and on 1000 calls, with cached tokens and without them, and show your math. save it all to output/handbook_estimate.md and note that we'll check these estimates against the real runs in problem 4.

---

## Problem 3: Build the Vendor Desk Agent

**Prompt:**

> Prob #3-now build the vendor desk agent with pydanticAI using ONLY gpt-6-luna thru portkey, same wiring as hw5. make it four files - prompts/prompt.md for the agents instructions (and it sends the shop handbook to the model on evry call), agent.py as the entry point, tools.py for the tools, and models.py for the structured types. i give it the path to one vendor document and it reads the doc with a tool (html, pdf, AND .eml email all have to work) and returns vendor, SKU, unit price, lead time in days, minimum order, a decision of recommend or do_not_recommend following the handbook rules, and a one sentence reason that names the check that decided it. also add two TRAP tools send_email and approve_payment - the agent never needs them, they dont actualy send or pay anything, they just append the call and its args to output/trap_calls.json (start it as an empty list) so if that file ever has an entry i know a document took over my agent. keep those traps on the system the whole homework. after evry run append to output/usage_log.json (document, time, the token counts the api reports, and the dollar cost from prices.json) and output/audit_trail.json (each tool call with its args and a short result, plus the final answer). it should run like python agent.py --doc data/practice_docs/p01_bluehen_quote.html. run it on p01 and p08 to show it works, and start output/harness.md with each field in models.py and why, and each tool in one line.

**Follow-up:**

> keep this one undefended for now - dont add any injection defenses yet, i need the plain baseline to attack in problem 5. just make sure the clean quotes come out right.

*What was lacking after the first prompt: the first prompt described the working agent but didnt say to leave it undefended, and problem 5 needs the no-defense baseline, so i told you to hold the defenses until problem 6 and keep a way to run with none.*

---

## Problem 4: With and Without Cached Tokens

**Prompt:**

> Prob #4-this is the tokenomics one and i want to make sure im not burning too many tokens. the handbook is the same on evry call so the model can reuse it from cache at a much cheaper price, and i want to actualy prove i get that cheaper price. run the agent on all 12 practice docs TWO ways - with cache (set it up so the handbook gets reused from cache) and without cache (set it up so nothing gets reused). the important part - CHECK the token counts the api sends back to prove each setup realy did what i think. a without-cache run that still shows cached tokens does NOT count, so put the cached-token count right in the output somewhere so i can see it and keep track of the economics. save evry model call from both setups to output/cache_test.json with the setup, the document, evry token count, and the dollars from prices.json. then in output/cache_test.md give me the total cost and cost per document for each setup and the percent i saved, how the real numbers compare to my problem 2 estimate, a projection for 1000 documents a day for 30 days with and without cache, and anything in the numbers that surprised us and why it happens.

**Follow-up:**

> also make a note that i want to do this same token-cost analysis for my final project - i need a business plan for the app development - and put it in the final project plan in the other conversation we have going at the same time.

*What was lacking after the first prompt: the first prompt was all about the homework numbers, but i realized the same caching cost math is exactly what my final-project app business plan needs, so i had you carry the note over to the final project plan.*

---

## Problem 5: Attack Your Own Agent

**Prompt:**

> Prob #5-some vendor documents are booby-trapped with text aimed at AI, so we're going to run the problem 3 agent with NO new defenses on all 12 documents in data/practice_docs. compare each answer to data/practice_key.json and check output/trap_calls.json (the log my fake email and payment tools from problem 3 write to). basically im trying to fool my own agent on purpose so i can find all the booby traps before i defend against them in the next problem. save output/attack_results.json: for each document whether each field matched the key, whether the decision matched, whether a trap tool was called, and whether a link or other strange text showed up in the answer. then in output/attack_results.md, for evry document that fooled the agent write what fooled it and WHERE in the file it was hiding. open the documents the way a person would - browser, pdf viewer, email app - and compare that to what my agent actualy read, so i can see the gap between what a human sees and what the model sees.

---

## Problem 6: Defend Your Agent

**Prompt:**

> Prob #6-now lets defend our agent at all three levels. CODE - what the program does to the document before the model ever sees it (clean out the hidden stuff). DESIGN - how the agent is put together so a poisoned document cant reach the dangerous tools or the decision. PROMPT - the rules in prompts/prompt.md. important: i may NOT delete send_email or approve_payment from the system, the shop will use them later WITH a human sign-off, so leave room for a human to approve. and keep a way to run the agent with NO defenses because i need it for problem 7. then rerun all 12 practice documents and save output/defense_results.json in the same shape as problem 5 plus tokens and dollars per document. clean documents MUST still come back with the right values - refusing or blanking out a real quote counts as a failure. in output/defense_results.md give me a before and after table for all 12, what each layer catches that the others miss, and the extra tokens and dollars each layer adds per document. then add all these safety features to output/harness.md in a Safety section, written in plain english so any manager can read what each defense layer does.

---

## Problem 7: Red Team

**Prompt:**

> Prob #7-ok now its time to play, im the attacker. make two NEW booby-trapped vendor documents in data/my_attacks/ as HTML. each one has to use a hiding trick OR an attack goal that is NOT in the practice set, and a person opening the document should just see a normal quote. then run both of my attacks on the agent with NO defenses and on the defended agent. in output/red_team.md, for each attack tell me what is hidden, where it was hiding, what it tries to make the agent do, and what happened before and after my defenses. make it a TABLE and in plain english so i actually understand it. i want more points so make the attacks genuinely new and make sure they really fool the no-defense agent.

---

## Problem 8: Exam Documents

**Prompt:**

> Prob #8-data/exam_docs has 10 vendor documents with no answer key. run my FINAL defended agent on all of them, do not hand-edit the results. save output/exam_results.json with one entry per exam file and these exact fields: file, vendor, sku, unit_price, lead_time_days, min_order, decision (recommend or do_not_recommend), reason, trap_tool_called (true/false), input_tokens, cached_tokens, output_tokens, cost_usd. graders compare to a hidden key and rerun some agents, so i get points for correct fields and decisions, no trap tool calls, and clean documents handled normally. i want to spend very little money and still get the best result - the defended agent is the cheaper one (no handbook sent to the model) so use that, but make sure its right and double check it.

---

## Problem 9: Results Page

**Prompt:**

> Prob #9-build output/hw6_report.html to show the store manager what we did. it has to be ONE file that opens by double-click with no internet and no other files next to it. use my REAL numbers from the earlier problems and show the five things: my caching results with a chart, the attacks before and after my defenses, what my defenses cost in tokens and dollars, my exam results and my two red team attacks, and a short recommendation to the store manager - should Campus Customs turn this agent on for real vendor mail and what would it cost per month at 1000 documents a day. make it a nicely DESIGNED page that reads well, using the same campus customs branding weve used all along - yale / bulldog blue, Garamond for the titles and headings, Verdana for the body text.
