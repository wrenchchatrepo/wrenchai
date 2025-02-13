# GitHub Labels

## Phase Labels
- `phase: mvp-1` - MVP Phase 1: Core Functionality
- `phase: mvp-2` - MVP Phase 2: Testing & Quality
- `phase: post-mvp` - Post-MVP Enhancements

## Priority Labels
### MVP Priorities
- `priority: p0` - Critical for MVP functionality
- `priority: p1` - Important for MVP but not blocking

### Post-MVP Priorities
- `priority: high` - Next phase critical features
- `priority: medium` - Nice to have features
- `priority: low` - Future enhancements

## Component Labels
- `component: super-agent` - SuperAgent related
- `component: inspector-agent` - InspectorAgent related
- `component: journey-agent` - JourneyAgent related
- `component: bayesian` - Bayesian reasoning system
- `component: infrastructure` - Infrastructure and deployment
- `component: testing` - Testing and QA
- `component: docs` - Documentation

## Status Labels
- `status: in-progress` - Work has started
- `status: blocked` - Blocked by dependencies
- `status: ready` - Ready for implementation
- `status: review-needed` - Needs code review

## Type Labels
- `type: bug` - Bug fixes
- `type: feature` - New features
- `type: enhancement` - Improvements to existing features
- `type: documentation` - Documentation updates
- `type: test` - Test-related changes
- `type: infrastructure` - Infrastructure changes

## Special Labels
- `dependencies` - Has dependencies that need to be completed first
- `good-first-issue` - Good for newcomers
- `help-wanted` - Extra attention is needed
- `do-not-merge` - Not ready to be merged

## Label Colors
- Phase Labels: `#C2E0C6` (Light Green)
- Priority Labels: `#D93F0B` (Red)
- Component Labels: `#0366D6` (Blue)
- Status Labels: `#FEF2C0` (Yellow)
- Type Labels: `#BFD4F2` (Light Blue)
- Special Labels: `#7057FF` (Purple)

## Label Usage Guidelines

1. Every issue must have:
   - One phase label
   - One priority label
   - One component label
   - One status label
   - One type label

2. Special labels are optional and can be combined with other labels

3. Priority label rules:
   - MVP tasks must use P0 or P1
   - Post-MVP tasks must use high/medium/low

4. Status label updates:
   - Update when work begins (in-progress)
   - Update when blocked (blocked)
   - Update when ready for review (review-needed)

5. Dependencies:
   - Add `dependencies` label to any issue that depends on other issues
   - Link to dependent issues in the issue description
