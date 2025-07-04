/// <reference types="cypress" />

describe('Security Report Page', () => {
  beforeEach(() => {
    // Mock user authentication
    cy.intercept('GET', '/api/v1/user/', {fixture: 'user.json'}).as('getUser');
    cy.intercept('GET', '/config', {fixture: 'config.json'}).as('getConfig');
    cy.intercept('GET', '/csrf_token', {fixture: 'csrfToken.json'}).as(
      'getCsrfToken',
    );

    // Mock notifications endpoint
    cy.intercept('GET', '/api/v1/user/notifications', {
      statusCode: 200,
      body: {notifications: []},
    }).as('getNotifications');

    // Mock repository data
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/tag/?limit=100&page=1&onlyActiveTags=true&specificTag=security',
      {fixture: 'single-tag.json'},
    ).as('getTag');
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be',
      {fixture: 'manifest.json'},
    ).as('getManifest');
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be?include_modelcard=true',
      {fixture: 'manifest.json'},
    ).as('getManifestWithModelCard');
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/labels',
      {fixture: 'labels.json'},
    ).as('getLabels');
  });

  it('render no vulnerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/noVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.contains(
      'Quay Security Reporting has detected no vulnerabilities',
    ).should('exist');
    cy.get('[data-testid="vulnerability-chart"]').within(() =>
      cy.contains('0'),
    );
    cy.get('td[data-label="Advisory"]').should('have.length', 0);
  });

  it('render mixed vulnerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.contains(
      'Quay Security Reporting has detected 41 vulnerabilities',
    ).should('exist');
    cy.contains('Patches are available for 30 vulnerabilities').should('exist');
    cy.get('[data-testid="vulnerability-chart"]').within(() =>
      cy.contains('41'),
    );
    cy.get('td[data-label="Advisory"]').should('have.length', 20);

    cy.get('button:contains("1 - 20 of 41")').first().click();
    cy.contains('100 per page').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 41);
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.get('[data-label="Severity"]')
        .get('span:contains("Critical")')
        .should('have.length', 3);
      cy.get('[data-label="Severity"]')
        .get('span:contains("High")')
        .should('have.length', 12);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Medium")')
        .should('have.length', 22);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Low")')
        .should('have.length', 2);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Unknown")')
        .should('have.length', 2);
    });
  });

  it('only show fixable', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
    cy.get('button:contains("1 - 20 of 41")').first().click();
    cy.contains('100 per page').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 41);
    cy.get('#fixable-checkbox').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 30);
    cy.contains('(None)').should('not.exist');
    cy.get('#fixable-checkbox').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 41);
  });

  it('filter by name', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
    cy.get('input[placeholder="Filter Vulnerabilities..."]').type('python');
    cy.get('td[data-label="Advisory"]').should('have.length', 7);
    cy.get('td[data-label="Package"]')
      .filter(':contains("python")')
      .should('have.length', 7);
  });

  it('render unsupported state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/unsupported.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.contains('Security scan is not supported.').should('exist');
    cy.contains('Image does not have content the scanner recognizes.').should(
      'exist',
    );
  });

  it('render failed state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/failed.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.contains('Security scan has failed.').should('exist');
    cy.contains('The scan could not be completed due to error.').should(
      'exist',
    );
  });

  it('render queued state', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/queued.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.contains('Security scan is currently queued.').should('exist');
    cy.contains('Refresh page for updates in scan status.').should('exist');
    cy.contains('Reload').should('exist');
  });

  // // TODO: Test needs to be implemented
  // it('renders vulnerability description', () => {
  //     cy.visit('/tag/quay/postgres/securityreportqueued?tab=securityreport');
  // });

  it('paginate values', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getSecurityReport');
    cy.contains('1 - 20 of 41').should('exist');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);

    // Change per page
    cy.get('button:contains("1 - 20 of 41")').first().click();
    cy.contains('20 per page').click();
    cy.get('td[data-label="Advisory"]').should('have.length', 20);

    // cycle through the pages
    cy.get('button[aria-label="Go to next page"]').first().click();
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
    cy.get('button[aria-label="Go to next page"]').first().click();
    cy.get('td[data-label="Advisory"]').should('have.length', 1);

    // Go to first page
    cy.get('button[aria-label="Go to first page"]').first().click();
    cy.contains('CVE-2019-12900').should('exist');

    // Go to last page
    cy.get('button[aria-label="Go to last page"]').first().click();
    cy.contains('pyup.io-47833 (PVE-2022-47833)').should('exist');

    // Switch per page while while being on a different page
    cy.get('button:contains("41 - 41 of 41")').first().click();
    cy.contains('20 per page').click();
    cy.contains('1 - 20 of 41').should('exist');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
  });

  it('render default desc sorted vlunerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getDescSortedSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getDescSortedSecurityReport');
    cy.get('td[data-label="Advisory"]').should('have.length', 20);
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.get('[data-label="Severity"]')
        .get('span:contains("Critical")')
        .should('have.length', 3);
      cy.get('[data-label="Severity"]')
        .get('span:contains("High")')
        .should('have.length', 12);
    });
  });

  it('render asc sorted vlunerabilities', () => {
    cy.intercept(
      'GET',
      '/api/v1/repository/user1/hello-world/manifest/sha256:1234567890101112150f0d3de5f80a38f65a85e709b77fd24491253990f306be/security?vulnerabilities=true',
      {fixture: 'security/mixedVulns.json'},
    ).as('getAscSortedSecurityReport');
    cy.visit('/repository/user1/hello-world/tag/security?tab=securityreport', {
      timeout: 10000,
    });
    cy.wait('@getUser');
    cy.wait('@getConfig');
    cy.wait('@getCsrfToken');
    cy.wait('@getNotifications');
    cy.wait('@getManifestWithModelCard');
    cy.wait('@getAscSortedSecurityReport');
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.get('#severity-sort').find('button').click();
    });
    cy.get('[data-testid="vulnerability-table"]').within(() => {
      cy.get('[data-label="Severity"]')
        .get('span:contains("Unknown")')
        .should('have.length', 2);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Low")')
        .should('have.length', 2);
      cy.get('[data-label="Severity"]')
        .get('span:contains("Medium")')
        .should('have.length', 16);
    });
  });
});
