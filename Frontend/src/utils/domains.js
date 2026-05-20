export function cloneDomainMap(domains) {
  return Object.fromEntries(
    Object.entries(domains || {}).map(([domain, subdomains]) => [
      domain,
      Array.isArray(subdomains) ? [...subdomains] : [],
    ]),
  );
}

export function normalizeDomains(rawDomains, exploredDomains = {}) {
  if (!rawDomains) {
    return [];
  }

  if (Array.isArray(rawDomains)) {
    return rawDomains.map((domain) => {
      const domainName = domain.domain || domain.name || domain.title || "Untitled Domain";
      const subdomains = domain.subdomains || domain.sub_domains || domain.children || [];

      return {
        name: domainName,
        isComplete: Boolean(domain.is_complete || domain.completed),
        subdomains: normalizeSubdomains(domainName, subdomains, exploredDomains),
      };
    });
  }

  return Object.entries(rawDomains).map(([domainName, subdomains]) => ({
    name: domainName,
    isComplete:
      Array.isArray(exploredDomains[domainName]) &&
      Array.isArray(subdomains) &&
      subdomains.length > 0 &&
      exploredDomains[domainName].length >= subdomains.length,
    subdomains: normalizeSubdomains(domainName, subdomains, exploredDomains),
  }));
}

function normalizeSubdomains(domainName, subdomains, exploredDomains) {
  if (!Array.isArray(subdomains)) {
    return [];
  }

  return subdomains.map((subdomain) => {
    const name =
      typeof subdomain === "string"
        ? subdomain
        : subdomain.subdomain || subdomain.name || subdomain.title || "Untitled Subdomain";
    const exploredSubdomains = exploredDomains?.[domainName] || [];

    return {
      name,
      isComplete:
        Boolean(typeof subdomain === "object" && (subdomain.is_complete || subdomain.completed)) ||
        exploredSubdomains.includes(name),
    };
  });
}

export function extractDomainsFromAgentState(agentState) {
  const rawDomains =
    agentState?.domains_to_explore ||
    agentState?.domainsToExplore ||
    agentState?.domains ||
    agentState?.domain_subdomains ||
    agentState?.domain_map ||
    agentState?.data?.domains_to_explore ||
    agentState?.data?.domainsToExplore ||
    agentState?.data?.domains ||
    {};

  const exploredDomains = agentState?.domains_explored || agentState?.completed_domains || {};

  return normalizeDomains(rawDomains, exploredDomains);
}

export function extractRawDomains(agentState) {
  return cloneDomainMap(
    agentState?.domains ||
      agentState?.domains_to_explore ||
      agentState?.data?.domains ||
      agentState?.data?.domains_to_explore ||
      {},
  );
}

export function applyExploredState(domains, exploredDomains = {}) {
  return domains.map((domain) => {
    const exploredSubdomains = exploredDomains[domain.name] || [];
    const subdomains = domain.subdomains.map((subdomain) => ({
      ...subdomain,
      isComplete: exploredSubdomains.includes(subdomain.name),
    }));

    return {
      ...domain,
      subdomains,
      isComplete: subdomains.length > 0 && subdomains.every((subdomain) => subdomain.isComplete),
    };
  });
}
