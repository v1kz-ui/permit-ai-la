# ADR-005: Five-Language Support from Day One

## Status
Accepted

## Context
LA's fire-affected communities include significant Korean, Chinese, and Filipino populations alongside English and Spanish speakers. Equitable access requires multilingual support from launch, not as an afterthought.

## Decision
Support 5 languages from MVP launch:
- English (en)
- Spanish (es)
- Korean (ko)
- Chinese Simplified (zh)
- Filipino/Tagalog (tl)

Implemented via:
- Mobile: react-i18next with per-language JSON bundles
- Backend notifications: language-keyed templates per notification type
- User model stores language preference

## Consequences
- All notification templates require 5 language variants
- Mobile app bundle slightly larger (5 locale files)
- UI must handle variable text lengths (Korean/Chinese compact, Spanish verbose)
- Ensures equitable access for LA's diverse fire-rebuild communities
