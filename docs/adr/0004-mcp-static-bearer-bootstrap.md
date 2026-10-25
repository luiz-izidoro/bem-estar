# ADR 0004 — Static Bearer as MCP bootstrap authentication

Status: Accepted

## Context

Bem Estar is a private single-user MCP resource server. Different clients have different authentication capabilities. Some can attach a preconfigured HTTP Bearer token directly; hosted clients may require OAuth browser discovery.

## Decision

Bootstrap with a dedicated high-entropy MCP Bearer token and the MCP SDK `TokenVerifier` boundary. Never reuse the HAE token, Dashboard session secret or Grafana credentials.

Static Bearer is not represented as a home-grown OAuth Authorization Server. When a client requires OAuth/OIDC, integrate a real external Authorization Server/IdP at the verifier boundary.

## Consequences

- simple personal clients can connect immediately;
- MCP remains authenticated, never anonymous;
- OAuth-capable hosted clients may require a later IdP integration;
- tool/resource/domain logic remains independent of the auth provider.
