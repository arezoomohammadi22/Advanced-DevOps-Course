# Infrastructure as Code and Pulumi Fundamentals

This guide builds a complete mental model of Infrastructure as Code (IaC) and Pulumi before moving into implementation. It begins with the operational problems created by manually managed infrastructure, develops the concepts of desired state, actual state, state tracking, idempotency, reproducibility, drift, and dependency management, and then explains how Pulumi turns a program written in a general-purpose language into real resources on a cloud platform, Kubernetes cluster, SaaS platform, or local infrastructure API.

The goal is not to memorize a few CLI commands. The goal is to understand the system that exists behind those commands and to recognize the engineering responsibilities that remain after infrastructure has been expressed as code.

---

## Learning Outcomes

After working through this guide, you should be able to:

- Explain why manually provisioned infrastructure becomes unreliable as the number of resources, environments, teams, regions, and changes grows.
- Distinguish ordinary automation scripts from a complete Infrastructure as Code workflow.
- Define desired state, current recorded state, actual live state, idempotency, reproducibility, and infrastructure drift.
- Explain declarative and imperative approaches without incorrectly treating them as mutually exclusive.
- Describe the practical benefits and limitations of IaC.
- Identify the boundary between infrastructure provisioning, configuration management, application deployment, containers, and Kubernetes.
- Explain why Pulumi uses general-purpose programming languages while still providing a declarative resource model.
- Describe the responsibilities of the Pulumi CLI, language runtime, SDK, engine, provider, resource graph, project, stack, state, and backend.
- Explain what happens during `pulumi preview`, `pulumi up`, `pulumi refresh`, and `pulumi destroy`.
- Compare Pulumi conceptually with Terraform, AWS CloudFormation, and Ansible.
- Recognize cases where Pulumi is a strong choice and cases where adoption requires further evaluation.

---

## Contents

1. [What Infrastructure Includes](#what-infrastructure-includes)
2. [Why Manual Infrastructure Becomes a Separate Engineering Problem](#why-manual-infrastructure-becomes-a-separate-engineering-problem)
3. [Why Scripts Alone Are Not Always Infrastructure as Code](#why-scripts-alone-are-not-always-infrastructure-as-code)
4. [What Infrastructure as Code Means](#what-infrastructure-as-code-means)
5. [IaC as a Process and Operating-Model Change](#iac-as-a-process-and-operating-model-change)
6. [Infrastructure Lifecycle](#infrastructure-lifecycle)
7. [Desired State, Recorded State, and Actual State](#desired-state-recorded-state-and-actual-state)
8. [Idempotency](#idempotency)
9. [Reproducibility](#reproducibility)
10. [Infrastructure Drift](#infrastructure-drift)
11. [Declarative and Imperative Models](#declarative-and-imperative-models)
12. [Operational Benefits of IaC](#operational-benefits-of-iac)
13. [Limitations and Responsibilities](#limitations-and-responsibilities)
14. [What IaC Is Not](#what-iac-is-not)
15. [Why Pulumi](#why-pulumi)
16. [General-Purpose Languages in Infrastructure](#general-purpose-languages-in-infrastructure)
17. [How Pulumi Remains Declarative](#how-pulumi-remains-declarative)
18. [Pulumi Architecture](#pulumi-architecture)
19. [Resources, Projects, Stacks, Configuration, and Secrets](#resources-projects-stacks-configuration-and-secrets)
20. [State and Backends](#state-and-backends)
21. [Preview, Update, Refresh, and Destroy](#preview-update-refresh-and-destroy)
22. [Dependency Graph and Execution Order](#dependency-graph-and-execution-order)
23. [Pulumi Compared with Other Tools](#pulumi-compared-with-other-tools)
24. [When Pulumi Is a Good Fit](#when-pulumi-is-a-good-fit)
25. [When Adoption Requires More Evaluation](#when-adoption-requires-more-evaluation)
26. [End-to-End Mental Model](#end-to-end-mental-model)
27. [Common Misconceptions](#common-misconceptions)
28. [Review Questions and Exercises](#review-questions-and-exercises)
29. [Official References](#official-references)

---

## What Infrastructure Includes

Source code is not enough to deliver a production service. An application needs a place to execute, a network path through which users and other services can reach it, a way to store data, security controls, observability, backup, and a recovery strategy. Depending on the architecture, it may also require load balancing, DNS, TLS certificates, caches, queues, identity policies, secrets, content delivery, and multiple isolated environments.

Infrastructure therefore includes much more than servers. Examples include:

- Virtual machines and bare-metal hosts
- Virtual private networks, subnets, route tables, gateways, and firewall rules
- Security groups and network policies
- DNS records and TLS certificates
- Object storage buckets and block storage volumes
- Managed relational and NoSQL databases
- Message queues, event buses, and caches
- IAM users, roles, policies, and service identities
- Secret stores and encryption keys
- Load balancers, API gateways, CDNs, and ingress controllers
- Kubernetes clusters, namespaces, deployments, services, and custom resources
- Monitoring, logging, alerting, and backup resources
- Some SaaS settings that expose an infrastructure-style API

The common characteristic is not the vendor or resource type. The common characteristic is that the resource has a managed lifecycle, affects the security, availability, connectivity, or behavior of a system, and is normally created or modified through a control plane or API.

A small project can often be deployed manually. One person creates a virtual machine, opens a port, installs the application, and records a few notes. The difficulty appears when that single environment becomes development, test, staging, and production; when the team introduces multiple accounts, regions, subscriptions, or clusters; or when each application release requires changes to networking, identity, storage, or routing. At that point, infrastructure is no longer a side task. It is a complex system with an independent lifecycle and independent operational risk.

### Architecture discovery exercise

For a simple online store, list everything required beyond application source code. Begin with compute and a database, then add DNS, TLS, backup, monitoring, cache, queueing, access control, deployment credentials, scaling, and disaster recovery. This exercise demonstrates why “infrastructure” should never be reduced to “a server.”

---

## Why Manual Infrastructure Becomes a Separate Engineering Problem

Consider a team deploying a web application to a public cloud. An operator enters the cloud console and creates a network, two subnets, a security group, a managed database, a load balancer, and a DNS record. The service becomes reachable, so the deployment appears successful. The engineering questions begin immediately afterward:

- What resources were created?
- Which exact properties were selected?
- Why were those properties selected?
- Which decisions were intentional and which were defaults?
- Can another engineer reproduce the same environment?
- Can a reviewer determine what changed and why?
- Can the environment be recovered after deletion or regional failure?
- Can the organization prove that production matches the approved architecture?

If the answers exist only in the operator's memory, screenshots, chat messages, or incomplete documentation, the organization does not have a reliable infrastructure system. It has a collection of human actions.

A second operator may create staging by following similar steps, but choose a different CIDR block, omit a security rule, use a different database size, forget required tags, or place a resource in the wrong availability zone. Development and staging may have similar names while being materially different. These small differences become expensive during incident response, security review, performance testing, and release validation.

Manual management also weakens auditability. Cloud audit logs can show that an API call occurred, but they do not always capture engineering intent, the associated ticket, the architecture decision, or the review that authorized the change. When infrastructure definitions live in version control, commits, pull requests, reviews, issue references, and release history can provide that missing context.

Recovery is another critical issue. “We built it once” is not a recovery strategy. A production team must know whether an environment can be rebuilt within a predictable time and with predictable results. If recovery depends on one specialist repeating undocumented steps, the process is not reliable.

### Common failure modes in manual provisioning

- Configuration differences between environments
- Undocumented changes
- Inconsistent naming and tagging
- Security rules applied differently across accounts
- Resources created in the wrong region or network
- Forgotten dependencies
- No reliable deletion or decommissioning process
- Recovery procedures that depend on individual memory
- Slow reviews because the intended architecture is not represented in a reviewable artifact
- Repeated effort for each new environment or customer

---

## Why Scripts Alone Are Not Always Infrastructure as Code

A natural response to console-driven work is to write shell, Python, PowerShell, or vendor CLI scripts. This is an important improvement because it automates repeatable actions. However, automation is broader than Infrastructure as Code. A script may say “create this network” without understanding whether the network already exists, what its current state is, what depends on it, whether a property can be updated in place, whether replacement is required, or how to recover after a partial failure.

A script that blindly creates a network can fail on the second execution or create a duplicate. Additional conditions can be added, but the script gradually begins to reimplement several hard problems:

- Resource identity
- State storage
- Difference calculation
- Dependency ordering
- Create/update/replace/delete decisions
- Partial-failure recovery
- Concurrency control
- Secret handling
- Change previews

IaC engines exist to standardize those responsibilities. They transform automation from a sequence of one-time commands into a managed model of infrastructure state and lifecycle.

> Every IaC workflow is automation, but not every automation script is a complete IaC system. The important test is not merely whether code exists. The important test is whether the system can model the desired state, understand managed resources, calculate differences, and control lifecycle operations reliably.

---

## What Infrastructure as Code Means

Infrastructure as Code is an engineering practice in which infrastructure is defined, provisioned, changed, and managed through machine-readable files or programs rather than being shaped primarily through manual console operations and temporary commands.

The phrase “as code” means more than syntax. It means that infrastructure should benefit from practices already proven in software engineering:

- Version control
- Peer review
- Automated checks
- Reusable modules and components
- Testing
- Repeatable execution
- Release management
- Traceable change history
- Controlled rollback or forward recovery
- Automated policy enforcement

In an IaC workflow, the team writes a definition that both people and machines can read. The definition describes the resources that should exist and the properties those resources should have. The IaC tool evaluates that definition, communicates with target-platform APIs, and creates or changes real resources. On later executions, it does not necessarily recreate everything. It evaluates the new desired state against recorded and, when requested, live state, then proposes only the required operations.

The resulting code is not the infrastructure itself. It is the approved intent from which the tool manages real infrastructure. This distinction matters because source code, recorded state, and live platform state can diverge.

---

## IaC as a Process and Operating-Model Change

Adopting an IaC tool without changing the surrounding workflow produces limited value. A mature process normally includes:

1. A change is made in a branch.
2. Formatting, linting, tests, and policy checks run.
3. A preview is generated.
4. Engineers review both the code and the proposed infrastructure operations.
5. The change is approved.
6. An automated identity applies the change to the intended stack.
7. Logs, state checkpoints, and outputs are retained.
8. Drift and failed operations are monitored.

This process moves infrastructure changes from individual action to team-owned change management. It creates a controlled path from intent to production.

However, version control alone does not guarantee safety. A repository can contain poor architecture, excessive permissions, public storage, destructive defaults, and weak secret handling. IaC makes change more visible and automatable; it does not automatically make the change correct.

### Repository and workflow decisions

A team must still decide:

- How repositories are organized
- How environments map to projects and stacks
- Which actors can preview or update production
- How credentials are obtained
- Where state is stored
- How state is backed up and recovered
- How provider and dependency versions are upgraded
- Which policies are mandatory
- How destructive operations are approved
- How emergency manual changes are reconciled back into code

---

## Infrastructure Lifecycle

Infrastructure is not created once and then forgotten. Every managed resource participates in a lifecycle:

1. **Design** — define the architecture, ownership, security boundary, and lifecycle expectations.
2. **Create** — provision the resource.
3. **Read/Observe** — inspect outputs, health, and live properties.
4. **Update** — change supported properties in place.
5. **Replace** — create a new resource and remove the old one when in-place update is impossible or unsafe.
6. **Import/Adopt** — bring an existing external resource under management.
7. **Refresh/Reconcile** — compare recorded knowledge with live state.
8. **Protect** — prevent accidental deletion when required.
9. **Retire/Destroy** — remove the resource in a controlled order.
10. **Recover** — respond to partial failure, interrupted operations, or state loss.

Create, update, replace, and delete are not equally risky. Replacing a stateless container is different from replacing a database. Deleting an empty development bucket is different from deleting a production data store. An IaC workflow must therefore be combined with operational review, backup, protection, and rollback or forward-recovery planning.

---

## Desired State, Recorded State, and Actual State

A correct mental model requires three related but different views of infrastructure.

### Desired state

Desired state is what the program or configuration says should exist. For example:

- A VPC with a particular CIDR block
- Three application replicas
- A database with encryption enabled
- A DNS record pointing to a load balancer
- A container exposing port 80 through host port 8080

### Recorded state

Recorded state is the IaC tool's stored knowledge of the resources it manages. In Pulumi, this includes resource identities, URNs, inputs, outputs, dependencies, provider references, and metadata required to manage future operations.

Recorded state is not merely a disposable cache. It participates in resource identity and lifecycle decisions. Losing or corrupting state can cause dangerous behavior, including duplicate creation, failed updates, or unexpected replacement.

### Actual state

Actual state is the live reality in the target platform at a specific moment. It is what the cloud API, Kubernetes API server, Docker daemon, or other provider currently reports.

These three views can differ:

- Code may request three replicas.
- Pulumi state may still record three replicas.
- A manual operator may have scaled the live deployment to six replicas.

That difference is drift. A refresh operation updates Pulumi's recorded understanding from the live provider. An update operation attempts to move the managed environment toward the desired program state.

### Why the distinction matters

A preview generally compares the desired program with Pulumi's current recorded state. Depending on the command and options, it may not perform a full refresh of every live resource first. Refreshing every resource can add API cost and latency, especially in large environments. Therefore, operators must understand when live refresh is required and must not assume every preview is a complete real-time audit of the target platform.

---

## Idempotency

An operation is idempotent when repeating it with the same desired input converges on the same result rather than continuously creating new resources or introducing further change.

In a healthy IaC workflow:

1. The first update creates the required resources.
2. The second preview, with no code or configuration changes and no drift, reports no changes.
3. Repeating the update does not create duplicate networks, containers, databases, or policies.

Idempotency is a property of the complete system, not just a keyword. Provider behavior, resource identity, naming, external APIs, random values, mutable image tags, timestamps, and program side effects can all weaken it.

### Threats to idempotency

- Creating random names on every program execution
- Reading unstable external data without controlling it
- Executing imperative side effects during program evaluation
- Using timestamps as resource properties
- Treating mutable tags as if they were immutable versions
- Failing to preserve resource identity during refactoring
- Bypassing the IaC engine with uncontrolled manual actions

---

## Reproducibility

Reproducibility is the ability to create equivalent environments predictably from controlled inputs. It does not always mean that every physical identifier is identical. Cloud-assigned IDs, IP addresses, and timestamps may differ. The goal is that architecture, policy, dependencies, and important properties are consistently reproduced.

A reproducible deployment requires more than an IaC file:

- Provider versions should be controlled.
- Language dependencies should be locked.
- Container images and artifacts should use stable versions or digests.
- Configuration should be explicit.
- Secrets should be available through a controlled system.
- External dependencies should be understood.
- Backend and credentials should be available.
- Manual post-deployment steps should be minimized or automated.

A repository that references “latest” everywhere, reads uncontrolled external data, and depends on undocumented manual setup is not truly reproducible even if it uses an IaC tool.

---

## Infrastructure Drift

Drift is the difference between approved infrastructure intent and live infrastructure reality. It can be caused by:

- Manual console changes
- Emergency incident actions
- Another automation system
- Autoscaling or controllers
- Provider-side defaults changing
- External deletion
- Security tools applying remediation
- Importing or adopting resources incorrectly
- Failed or interrupted updates

Not all drift should be handled identically. The operator must choose between two broad strategies:

### Remediation

Return actual state to the approved desired state. This is appropriate when the external change was accidental or unauthorized.

### Adoption

Modify code and, where necessary, state so the external change becomes the new approved intent. This is appropriate when the change was a valid emergency action or an intentional platform decision.

Blindly running refresh or update can be dangerous. A refresh can record an external change that should not be accepted. An update can erase a valid emergency fix. Reconciliation requires technical and operational judgment.

---

## Declarative and Imperative Models

### Imperative model

An imperative program emphasizes the sequence of actions:

1. Create a network.
2. Read its ID.
3. Create a subnet.
4. Create a server.
5. Attach a security rule.

The author explicitly controls how operations are performed.

### Declarative model

A declarative program emphasizes the target result:

- A network should exist with these properties.
- A subnet should reference that network.
- A server should exist in the subnet.
- A rule should allow a specific traffic path.

The engine calculates the operations required to move from known state to desired state.

### Why the distinction is not absolute

Pulumi programs are written in languages that support loops, functions, conditions, classes, package calls, and ordinary control flow. That does not mean the infrastructure lifecycle becomes a simple imperative script. The program executes to register a desired resource graph. The Pulumi engine then performs diffing, dependency analysis, and lifecycle operations.

The program can therefore use imperative language features to produce a declarative resource model.

---

## Operational Benefits of IaC

### Repeatability and environment consistency

A shared program reduces accidental differences between development, staging, and production. Differences can be represented explicitly as configuration instead of being hidden in manual actions.

### Reviewable changes

Infrastructure changes can be reviewed through pull requests. Reviewers can evaluate both code and preview output before a production update.

### Faster environment creation

New environments, customers, regions, or test stacks can be created from reusable patterns rather than being rebuilt manually.

### Better auditability

Commits, reviews, CI logs, update history, and state checkpoints provide a stronger audit trail than screenshots and personal notes.

### Recovery and disaster testing

IaC improves the ability to recreate architecture, though data recovery still requires backups, replication, and restore procedures.

### Reuse and standardization

Teams can create reusable components for approved networks, Kubernetes platforms, databases, logging, and security controls.

### Policy and security automation

Policy checks can reject public storage, unrestricted ingress, missing encryption, invalid regions, or absent tags before deployment.

### Collaboration between software and platform teams

A common programming model can reduce the boundary between application engineering and infrastructure engineering, provided ownership and security boundaries remain clear.

---

## Limitations and Responsibilities

IaC is not a magic safety system. It introduces new responsibilities:

- State must be secured and backed up.
- Credentials must follow least privilege.
- Secrets must not be committed as plaintext.
- Provider and runtime upgrades must be controlled.
- Code quality matters.
- Reusable abstractions can become overly complex.
- Preview output must be reviewed rather than blindly approved.
- Concurrency and locking must be managed.
- Imported resources require careful identity handling.
- Some changes still cause downtime or data loss.
- APIs can fail or behave asynchronously.
- Partial deployments require recovery procedures.

The ability to write loops and conditions is powerful, but it also allows poor engineering. A program that dynamically creates hundreds of resources from unstable inputs can be more dangerous than a static template. Power must be combined with coding standards, testing, review, and a clear operating model.

---

## What IaC Is Not

### IaC is not automatically configuration management

Infrastructure provisioning usually manages external resources such as networks, VMs, databases, and clusters. Configuration management tools such as Ansible often manage packages, files, services, and operating-system settings inside machines. The boundaries can overlap, but the lifecycle models are different.

A common architecture is:

- Pulumi creates networks, instances, IAM, and load balancers.
- Ansible configures software inside the instances.

In container-based environments, image builds may replace much of traditional server configuration.

### IaC is not the same as application deployment

Creating a Kubernetes cluster is infrastructure provisioning. Deploying an application into that cluster may also be represented with IaC, Helm, GitOps, or a deployment controller. These layers can share tools, but they still have different release cadences and ownership.

### IaC is not a container image

A container image packages application runtime content. It does not by itself create networks, IAM roles, databases, DNS records, or clusters.

### IaC is not Kubernetes itself

Kubernetes has its own declarative control model. Pulumi can create Kubernetes objects and can also create the underlying cluster and related cloud resources. Kubernetes continuously reconciles cluster objects, while Pulumi manages resources during IaC operations. Understanding both state models is important.

### IaC does not eliminate observation or emergency access

Operators may still use consoles and CLI tools for troubleshooting and incident response. The rule is that durable changes should return to the approved code and workflow so the repository remains the source of intent.

---

## Why Pulumi

Pulumi is an Infrastructure as Code platform that allows infrastructure to be defined using general-purpose languages such as TypeScript/JavaScript, Python, Go, .NET languages, Java, and YAML.

Pulumi is useful when teams want to combine the lifecycle model of an IaC engine with the abstraction, testing, package management, and reuse capabilities of normal programming languages.

Pulumi can manage resources through many providers, including:

- AWS
- Microsoft Azure
- Google Cloud
- Kubernetes
- Docker
- GitHub
- Cloudflare
- Datadog
- SaaS and platform APIs exposed through providers

The important point is not merely that Pulumi code “looks like application code.” The important point is that a Pulumi program registers resources with an engine that tracks identity, state, dependencies, and lifecycle.

---

## General-Purpose Languages in Infrastructure

Using a real programming language provides:

- Functions and modules
- Loops and conditions
- Classes and component abstractions
- Package ecosystems
- Static type checking in languages such as TypeScript, Go, Java, and C#
- Unit-test frameworks
- Integration with application libraries and internal APIs
- Familiar IDE features and debugging tools
- Reusable domain-specific platform components

Examples of practical use include:

- Creating one subnet per availability zone from a typed list
- Applying a standard tagging function to all resources
- Enforcing naming conventions through helper functions
- Building a reusable application-platform component
- Generating environment-specific resources from structured configuration
- Testing that no storage bucket is public
- Combining infrastructure creation with an internal service catalog

### Risks of excessive abstraction

Infrastructure code should not hide the platform so completely that operators cannot understand what will be created. Deep inheritance, uncontrolled metaprogramming, side effects, and complex factory layers can make previews difficult to interpret. Good abstractions reduce repetition while preserving operational clarity.

---

## How Pulumi Remains Declarative

A Pulumi program executes like a normal program, but the important output is a set of resource registrations and relationships. Consider the conceptual flow:

1. The language runtime starts the program.
2. The program creates resource objects using a Pulumi SDK.
3. Each resource declaration is registered with the Pulumi engine.
4. Inputs containing other resource outputs establish dependencies.
5. The engine builds a desired resource graph.
6. The engine compares that graph with stored state.
7. Providers calculate detailed differences and perform API operations.
8. New outputs and checkpoint data are written to the backend.

The engine, not ordinary program execution order alone, controls the infrastructure lifecycle.

---

## Pulumi Architecture

### Pulumi program

The program is the source code that declares the desired resources. It may include ordinary language logic, configuration reads, reusable components, and exported outputs.

### Pulumi CLI

The CLI is the main local entry point. It:

- Finds the active project
- Selects the active stack
- Connects to the backend
- Starts the language runtime
- Starts previews and updates
- Coordinates providers
- Displays diagnostics and progress
- Reads and writes configuration
- Manages stack lifecycle

Core commands introduced by this model are:

```bash
pulumi preview
pulumi up
pulumi refresh
pulumi destroy
```

### Language runtime

The language runtime executes the program in the selected language. For TypeScript, Node.js is the runtime. For Python, the Python interpreter is used. The runtime is responsible for executing program logic and communicating resource registrations to the engine.

### Pulumi SDK

The SDK supplies core types and functions such as configuration access, outputs, resource registration, interpolation, project name, and stack name. Provider packages expose platform-specific resource types.

### Pulumi engine

The engine is the central orchestrator. It:

- Receives resource registrations
- Builds the dependency graph
- Loads the previous checkpoint
- Computes planned operations
- Coordinates providers
- Orders creates and deletes
- Tracks failures and partial progress
- Writes a new checkpoint after successful progress

### Provider

A provider translates Pulumi resource operations into target-platform API calls. The AWS provider understands AWS resources; the Kubernetes provider communicates with the Kubernetes API; the Docker provider communicates with Docker.

A provider is responsible for operations such as:

- Checking inputs
- Calculating detailed differences
- Creating resources
- Reading live state
- Updating resources
- Deleting resources
- Returning resource outputs

### State backend

The backend stores stack state and related metadata. Depending on the backend, it can also provide history, locking, encryption integration, access control, and collaboration features.

---

## Resources, Projects, Stacks, Configuration, and Secrets

### Resource

A resource is the fundamental managed unit. It has:

- A logical name in the Pulumi program
- A type
- Inputs
- Outputs
- A provider
- Dependencies
- A Pulumi URN
- Often a separate physical identifier assigned by the target platform

Logical identity should be treated carefully. Renaming a logical resource can cause the engine to interpret the change as deletion plus creation unless aliases or other migration mechanisms are used.

### Project

A project is the logical boundary of a Pulumi program and is described by `Pulumi.yaml`. It normally contains:

- Project name
- Runtime
- Description
- Optional main program location
- Language-specific options

A project is not itself a deployed environment. It is the reusable program definition.

### Stack

A stack is an isolated instance of a project. Typical stacks are `dev`, `staging`, and `production`. Each stack has independent:

- State
- Configuration
- Secrets
- Outputs
- Update history
- Managed resources

A stack is not the same as a Git branch. A branch is a source-control concept. A stack is a real deployment boundary with live resources and stored state.

### Configuration

Configuration holds values that differ between stacks, such as:

- Region
- Port
- Instance size
- Replica count
- Domain name
- Image version
- Feature flags
- Retention period

Configuration avoids duplicating the entire program for each environment.

### Secrets

Secrets are encrypted configuration values or output values marked as sensitive. Encryption protects stored representation and helps prevent accidental display, but the plaintext still exists at runtime where a provider or target platform may need it. Secret handling therefore also requires least privilege, secure CI logs, backend access control, and careful downstream use.

---

## State and Backends

Pulumi state stores the checkpoint for each stack. It includes enough information to identify and manage resources across future operations. State can contain:

- Resource URNs
- Provider references
- Inputs and outputs
- Parent/child relationships
- Dependencies
- Physical IDs
- Secret ciphertext
- Pending or completed operation metadata

Backends may include Pulumi Cloud or supported self-managed object/file storage backends. A local backend is useful for isolated labs, but shared environments need stronger collaboration controls.

### Backend requirements for serious use

- Encryption at rest
- Access control
- Backups
- Recovery procedures
- Concurrency control or locking
- Audit history
- Separation between environments
- Secure credential handling
- Defined ownership

### Pulumi Cloud and the open-source CLI

Pulumi's CLI and core IaC capabilities can work with Pulumi Cloud or self-managed backends. Pulumi Cloud adds managed collaboration, deployment history, access controls, policy and automation integrations, and other platform services. A team should choose based on security, compliance, collaboration, operational ownership, and cost requirements.

---

## Preview, Update, Refresh, and Destroy

### `pulumi preview`

A preview evaluates the program and displays proposed operations without intentionally applying them. Conceptually, it:

1. Identifies project and stack.
2. Loads stack configuration and secrets.
3. Loads the prior checkpoint.
4. Executes the program through the language runtime.
5. Registers desired resources.
6. Builds the dependency graph.
7. Compares desired resources with stored resources.
8. Asks providers for detailed diffs where required.
9. Displays create, update, replace, delete, and same operations.

Preview is a risk-control mechanism, not a perfect prediction. External APIs, eventual consistency, permissions, quotas, dynamic values, and concurrent changes can still cause the real update to differ or fail.

### `pulumi up`

An update performs the deployment. It repeats program evaluation, calculates the plan, requests confirmation when interactive approval is enabled, then executes operations through providers in dependency order. After progress is made, Pulumi writes checkpoint information so future operations understand the resulting resource state.

A failed update can leave some resources created and others not created. This is why state checkpoints, diagnostics, refresh, and recovery procedures matter.

### `pulumi refresh`

Refresh reads live resource state from providers and updates Pulumi's recorded state. It is used to detect external changes, deleted resources, and property differences. Refresh does not by itself mean that external changes are approved. The resulting differences must be reviewed.

### `pulumi destroy`

Destroy removes resources managed by the selected stack, normally in reverse dependency order. Destroy does not automatically delete the stack record itself. Removing a stack is a separate lifecycle decision.

---

## Dependency Graph and Execution Order

Infrastructure order is based on dependencies, not simply on source-code line order.

Dependencies can be created implicitly when one resource input uses another resource output. For example:

- A subnet references a VPC ID.
- A VM references a subnet ID.
- A DNS record references a load-balancer hostname.
- A Kubernetes deployment references a ConfigMap name.

Pulumi uses these relationships to parallelize independent operations and order dependent operations safely.

Explicit dependencies are available when a real operational dependency is not visible through resource inputs. They should be used intentionally rather than added everywhere, because unnecessary explicit dependencies reduce concurrency and can hide poor resource modeling.

During deletion, dependency order is reversed: children and consumers are normally removed before the resources they depend on.

---

## Pulumi Compared with Other Tools

### Pulumi and Terraform

Both tools address Infrastructure as Code, provider-based resource management, state, diffing, dependencies, and multi-provider environments.

Key conceptual differences include:

- Terraform primarily uses HCL, a domain-specific configuration language.
- Pulumi primarily uses general-purpose languages and language package ecosystems.
- Pulumi abstractions can use ordinary functions, classes, interfaces, and test frameworks.
- Terraform has a very large established module ecosystem and broad organizational adoption.
- Pulumi's programming model can be attractive when platform logic and typed reusable components are important.

The decision should consider ecosystem maturity, team skills, existing modules, governance, state operations, upgrade strategy, and total migration cost—not syntax preference alone.

### Pulumi and AWS CloudFormation

CloudFormation is AWS-native and deeply integrated with AWS services, IAM, service catalogs, and AWS-managed stack operations. It is an appropriate choice for many AWS-only organizations.

Pulumi can manage AWS and other platforms from a common programming model. It is attractive when multi-provider workflows, reusable software abstractions, testing, or application integration are important.

Neither choice is universally superior. The operating context determines the better tool.

### Pulumi and Ansible

Ansible is primarily an automation and configuration-management tool. It is widely used for package installation, files, services, host configuration, and orchestration. It can also call cloud modules.

Pulumi is generally stronger for resource lifecycle, state, dependency graphs, previews, and create/update/replace/delete management. A real architecture can use both:

- Pulumi provisions networks and virtual machines.
- Ansible configures software inside the machines.

Container images, managed services, or immutable infrastructure can reduce the amount of in-host configuration required.

---

## When Pulumi Is a Good Fit

Pulumi is especially attractive when:

- The team already works effectively with TypeScript, Python, Go, .NET, or Java.
- Reusable platform components are important.
- Infrastructure must integrate with application or internal-platform code.
- Multiple providers must be managed in one workflow.
- Unit and integration testing are required.
- Typed configuration and IDE support provide value.
- A platform team is building self-service environment creation.
- The Automation API will be used to embed deployments in a service or portal.
- Complex but controlled conditional architecture is required.

---

## When Adoption Requires More Evaluation

Pulumi should not be selected only because its syntax appears familiar. Further evaluation is required when:

- The team lacks skill in the selected programming language.
- The organization already has a mature Terraform ecosystem, module registry, policy system, and support model.
- The use case is simple and fully served by a native platform tool.
- Dependency-management or package-supply-chain requirements are not understood.
- The proposed design relies on excessive inheritance or metaprogramming.
- State ownership and recovery are undefined.
- Provider upgrade and compatibility policies are undefined.
- The organization cannot support the required training and operational model.

Tool selection should account for the full lifecycle and organizational cost.

---

## End-to-End Mental Model

Imagine an organization creates an isolated environment for every customer. Each environment includes a network, Kubernetes namespace, database, object storage, and DNS record.

A Pulumi project defines the shared pattern. A stack represents one customer or one environment. Stack configuration contains region, domain, sizing, and retention values. Secrets are stored using an approved secret mechanism.

The onboarding workflow is:

1. Create or select the stack.
2. Set configuration and secrets.
3. Run policy and test checks.
4. Generate a preview.
5. Review the proposed operations.
6. Approve the change.
7. Run `pulumi up`.
8. The program registers resources.
9. The engine builds the graph and calculates differences.
10. Providers call target APIs.
11. Outputs such as endpoints and database hostnames are recorded.
12. The backend stores the updated checkpoint.

The decommissioning workflow must be equally deliberate. It may require data export, backup verification, protection removal, approval, resource destruction, and stack removal.

Pulumi is therefore not merely a replacement for console clicks. It can become part of a product and platform workflow.

---

## Common Misconceptions

### “Pulumi is just a cloud SDK”

A normal cloud SDK directly calls APIs and leaves lifecycle tracking to the application author. Pulumi resource declarations are registered with an engine that manages state, differences, dependencies, and lifecycle.

### “State is only a cache”

State participates in identity and lifecycle. Treating it as disposable is dangerous.

### “A stack is the same as a Git branch”

A branch contains source history. A stack owns configuration, state, outputs, and real managed resources.

### “Preview guarantees the exact update”

Preview is a strong safety mechanism, but external systems can change and API behavior can differ during execution.

### “Output values are ordinary strings”

A Pulumi `Output` represents a value that may only be known during deployment and also carries dependency and secret metadata.

### “IaC eliminates all manual operations”

Observation and emergency actions may still be manual. Durable changes must be reconciled into the approved code and state model.

### “Abstraction should be created immediately”

First understand the real platform resources and lifecycle. Create reusable components only after a stable pattern is known.

---

## Review Questions and Exercises

### Discussion questions

1. If the Pulumi program exists but the stack state is lost, why is the program alone not enough for safe management?
2. If an operator changes a resource in the cloud console and then runs `pulumi up`, what outcomes are possible?
3. Why does writing Pulumi in TypeScript or Python not make its resource model a simple imperative script?
4. For development, staging, and production, what should be shared in code and what should be stack-specific configuration?
5. Which kinds of changes commonly require resource replacement, and why is replacement review especially important in production?
6. When should drift be remediated, and when should it be adopted?
7. What controls are required around a shared production backend?

### Architecture exercise

Choose a simple web application and complete the following:

1. List all required resources beyond source code.
2. Identify dependencies between the resources.
3. Mark which values are common across environments.
4. Mark which values belong in stack configuration.
5. Identify sensitive values that must be treated as secrets.
6. Describe three realistic drift scenarios.
7. Decide whether each drift scenario should be remediated or adopted.
8. Define the Pulumi project boundary.
9. Define stack names.
10. Select the required providers.
11. Choose a state backend.
12. List useful stack outputs.
13. Describe what a safe preview should show for the first deployment.
14. Identify resources that require deletion protection, backup, or special replacement planning.

---

## Key Takeaways

- Infrastructure is a managed system, not merely a group of servers.
- Manual operations become unreliable as scale and change frequency increase.
- IaC introduces desired-state modeling, state tracking, diffing, dependencies, and controlled lifecycle operations.
- Desired state, Pulumi's recorded state, and live actual state are distinct.
- Idempotency and reproducibility require controlled inputs and disciplined engineering.
- Drift must be detected and reconciled intentionally.
- General-purpose language features can generate a declarative resource graph.
- Pulumi consists of a program, language runtime, SDK, engine, providers, stacks, and a state backend.
- Preview reduces risk but does not replace operational understanding.
- State security, secret handling, provider upgrades, testing, and recovery remain essential responsibilities.

---

## Official References

- Pulumi Documentation: <https://www.pulumi.com/docs/>
- Infrastructure as Code: <https://www.pulumi.com/docs/iac/>
- Pulumi Concepts: <https://www.pulumi.com/docs/iac/concepts/>
- How Pulumi Works: <https://www.pulumi.com/docs/iac/concepts/how-pulumi-works/>
- Projects: <https://www.pulumi.com/docs/iac/concepts/projects/>
- Stacks: <https://www.pulumi.com/docs/iac/concepts/stacks/>
- Resources: <https://www.pulumi.com/docs/iac/concepts/resources/>
- Providers: <https://www.pulumi.com/docs/iac/concepts/resources/providers/>
- State and Backends: <https://www.pulumi.com/docs/iac/concepts/state-and-backends/>
- Configuration and Secrets: <https://www.pulumi.com/docs/iac/concepts/config/>
- Drift Detection and Reconciliation: <https://www.pulumi.com/docs/deployments/deployments/drift/>
- Pulumi CLI: <https://www.pulumi.com/docs/iac/cli/>

> Product behavior, CLI options, provider schemas, and managed-service features can change over time. Check the current documentation before using commands in a production environment.
