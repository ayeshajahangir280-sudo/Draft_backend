# Draft Day Live

Create a polished, fully clickable **FRONTEND-ONLY DEMO** for a cricket **Player Draft System**.

IMPORTANT: This is only a client demonstration/prototype right now.

Do NOT build a backend.
Do NOT build a database.
Do NOT build APIs.
Do NOT implement real authentication.
Do NOT implement WebSockets.
Do NOT add unnecessary features.
Do NOT create an auction or bidding system.

Use local mock data and frontend state only.

The purpose is to demonstrate the exact draft workflow visually to the client before we build the real system.

# PRODUCT

Name:

**Stride Player Draft**

This is NOT an auction.

There is:

* No bidding
* No player prices
* No team purse
* No bid buttons

Managers simply take turns selecting players.

---

# DEMO SETUP

Create mock data for:

* 8 teams/managers
* Around 20–24 cricket players
* Player photos using suitable placeholder/profile images
* Player name
* Player category
* Playing role

Use categories:

A
B
C
D

Use roles such as:

Batsman
Bowler
All-Rounder
Wicket Keeper

---

# MAIN SCREEN

The main draft screen should look professional enough to show directly to a client.

Use a modern sports/cricket broadcast-style interface.

Desktop/laptop is the main priority.

The layout should have THREE important areas.

## LEFT — Draft Order

Create a vertical panel titled:

**DRAFT ORDER**

Show all 8 managers/teams in the randomized order.

Example:

1. Falcon Warriors
2. Yuva Force
3. Shuttle Shots
4. Asfar Amigos
5. Golden Axis Mavericks
6. Team Six
7. Team Seven
8. Team Eight

Clearly highlight the manager whose turn is currently active.

For example:

**CURRENT PICK**

Falcon Warriors

Also visually distinguish:

* Completed picks
* Current pick
* Upcoming picks

---

# CENTER — Main Draft Area

This should be the biggest and most visually impressive section.

Before a player is selected, display:

**FALCON WARRIORS ARE ON THE CLOCK**

and:

**Select a player from the available players**

When a player is selected, transform this area into a large selection announcement.

Example:

**PLAYER SELECTED**

[Large Player Photo]

**Ahmed Khan**

All-Rounder

Category A

**Selected by Falcon Warriors**

Make this feel like a professional sports draft announcement.

After a short visual state/animation, allow the demo to continue to the next manager.

Do not overdo animations.

---

# RIGHT — Available Players

Create a panel:

**AVAILABLE PLAYERS**

At the top, provide category filters:

A | B | C | D

Show player cards underneath.

Each card should contain:

* Player photo
* Player name
* Category
* Playing role
* SELECT button

Example:

Ahmed Khan
All-Rounder
Category A
[SELECT]

Bilal Ahmed
Batsman
Category A
[SELECT]

Usman Ali
Bowler
Category A
[SELECT]

Make this list scrollable so the overall page does not become extremely tall.

---

# PLAYER SELECTION DEMO

The prototype must actually be clickable.

When the active manager selects a player:

1. Show a confirmation modal.

Example:

**Confirm Player Selection?**

Ahmed Khan
Category A
All-Rounder

Selected by:

Falcon Warriors

[Cancel] [Confirm Selection]

2. When confirmed:

* Mark the player as selected.
* Remove the player from Available Players.
* Show the player prominently in the centre.
* Add the player to the current team's picks.
* Mark the current manager's turn as completed.
* Automatically activate the next manager.

Everything can happen using frontend state.

No backend is required.

---

# TURN SYSTEM

Only the currently active manager should appear able to select a player.

For demo purposes, simulate the active manager locally.

After a player is selected:

Manager 1 ✓
Manager 2 ← CURRENT
Manager 3
Manager 4
etc.

When all 8 managers have selected a player, show:

**ROUND 1 COMPLETE**

and a button:

**START NEXT ROUND**

---

# NEXT ROUND

When START NEXT ROUND is clicked:

Randomize the order of the same 8 managers again.

Display:

**ROUND 2**

Reset only the manager turn statuses.

DO NOT return previously selected players to the available list.

Previously selected players must remain assigned to their teams.

Then continue the same selection process.

---

# ADMIN DEMO CONTROLS

Because this is only a prototype, add a small unobtrusive:

**Demo Admin Controls**

It can contain:

Active Category:
[A] [B] [C] [D]

and:

**Randomize Draft Order**

**Start Next Round**

**Reset Demo**

Changing the active category should filter the available player list.

Keep these controls visually secondary because the client should focus on the draft experience.

---

# TEAM PICKS

Allow the user to click a manager/team in the Draft Order.

Open a small side panel/modal showing:

**Falcon Warriors**

Selected Players

Ahmed Khan — All-Rounder — Category A
Player 2 — Bowler — Category B

This demonstrates how the final team roster can be viewed.

---

# VISUAL STYLE

The interface should feel like a professional live cricket draft rather than a normal admin dashboard.

Use:

* Premium dark sports interface
* Strong typography
* Large player imagery
* Clean cards
* Clear hierarchy
* Subtle gradients
* Modern borders
* Good spacing
* Professional hover states
* Small tasteful animations
* Excellent readability

Avoid excessive neon effects.

Avoid making everything look like generic SaaS dashboard cards.

The CENTER player announcement should be the visual focus.

The UI must fit properly on a normal laptop screen.

Make it responsive, but prioritize desktop because the actual draft will primarily be operated on laptops.

---

# IMPORTANT DEMO BEHAVIOUR

The demo must demonstrate this exact sequence:

Admin chooses Category A

↓

System shows randomized manager order

↓

Manager 1 becomes active

↓

Manager 1 selects one available Category A player

↓

Confirmation

↓

Player is assigned to Manager 1

↓

Player disappears from Available Players

↓

Large PLAYER SELECTED announcement appears

↓

Manager 2 automatically becomes active

↓

Process continues

↓

All 8 managers complete their picks

↓

ROUND COMPLETE

↓

Admin starts next round

↓

Manager order can be randomized again

↓

Draft continues with remaining players

---

# VERY IMPORTANT — KEEP THE BUILD SMALL

Do NOT expand the scope.

Do NOT build:

* Backend
* Database
* Django
* Supabase
* Firebase
* Authentication
* User management
* WebSockets
* Deployment configuration
* Auction functionality
* Bidding
* Purse management
* Payments
* Tournament management
* Registration system
* Statistics
* Complex settings
* Separate unnecessary pages

This is ONLY a visual and interactive client demo of the player draft workflow.

Use reusable React components and local mock data.

Keep the implementation compact so that the prototype can be generated efficiently without wasting Lovable credits/tokens on unnecessary infrastructure.

FIRST build the complete main draft screen and make the core selection workflow functional.

If anything optional cannot be completed within the initial generation, prioritize in this exact order:

1. Main draft screen
2. Available players
3. Draft order
4. Player selection
5. Automatic next turn
6. Round completion
7. Next round/randomization
8. Team roster popup
9. Minor animations/polish

Do not spend generation effort on features outside this list.

The final result should be something I can open, click through for several picks, and immediately show my client to confirm:

**“Yes, this is how the draft system should work.”**

This project was built with [Lovable](https://lovable.dev).

## Build with Lovable

Continue developing this project in the [Lovable editor](https://lovable.dev/projects/9c8fb3b8-5eb3-4e1d-a5c1-1263c0b0ee57).

- **Ship faster**: describe what you want to build and Lovable handles the code.
- **Stay in sync**: every change made in Lovable is committed straight to this repository.
- **Full ownership**: this code is yours. Push to `main` on GitHub and your changes sync back into Lovable, ready for your next prompt.

## Development

Prefer working locally? You need Node.js and npm — [install with nvm](https://github.com/nvm-sh/nvm#installing-and-updating).

```sh
git clone <this-repository-url>
cd <repository-name>
npm i
npm run dev
```
