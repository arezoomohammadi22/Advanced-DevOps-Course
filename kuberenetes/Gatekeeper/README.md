
# Gatekeeper Installation and Configuration Guide

This document provides detailed steps for installing and configuring **Gatekeeper** on Kubernetes, along with custom **ConstraintTemplate** and **Constraint** for enforcing label requirements on resources.

## Prerequisites

- Kubernetes cluster
- `kubectl` command line tool
- `helm` package manager

## Step 1: Install Gatekeeper using kubectl

To install Gatekeeper using `kubectl`, run the following command:

```bash
kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/v3.14.0/deploy/gatekeeper.yaml
```

## Step 2: Install Gatekeeper using Helm

To install Gatekeeper using Helm, first, add the Gatekeeper Helm chart repository:

```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update
```

Then, install Gatekeeper with production settings:

```bash
helm install gatekeeper gatekeeper/gatekeeper   --namespace gatekeeper-system   --create-namespace   --set replicas=3   --set auditInterval=300   --set constraintViolationsLimit=100
```

## Step 3: Verify Installation

To verify the installation, run the following command:

```bash
kubectl get validatingwebhookconfigurations | grep gatekeeper
```

This should show the Gatekeeper webhook configuration.

## Step 4: Create ConstraintTemplate

Create a file named `constraint-template.yaml` with the following content:

```yaml
apiVersion: templates.gatekeeper.sh/v1
kind: ConstraintTemplate
metadata:
  name: k8srequiredlabels
  annotations:
    description: "Requires resources to have specified labels"
spec:
  crd:
    spec:
      names:
        kind: K8sRequiredLabels
      validation:
        openAPIV3Schema:
          type: object
          properties:
            message:
              type: string
              description: "Custom error message"
            labels:
              type: array
              description: "List of required labels"
              items:
                type: string
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package k8srequiredlabels

        violation[{"msg": msg}] {
          required_label := input.parameters.labels[_]
          not has_label(required_label)
          msg := get_message(required_label)
        }

        has_label(label) {
          input.review.object.metadata.labels[label]
        }

        get_message(label) = msg {
          input.parameters.message
          msg := sprintf("%s: %s", [input.parameters.message, label])
        }

        get_message(label) = msg {
          not input.parameters.message
          msg := sprintf("Resource is missing required label: %s", [label])
        }
```

Apply the `ConstraintTemplate`:

```bash
kubectl apply -f constraint-template.yaml
```

## Step 5: Create Constraint

Create a file named `constraint.yaml` with the following content:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-owner-label
spec:
  enforcementAction: deny
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
      - apiGroups: [""]
        kinds: ["Pod"]
    excludedNamespaces:
      - kube-system
      - gatekeeper-system
  parameters:
    message: "All deployments must have ownership labels"
    labels:
      - "owner"
      - "team"
```

Apply the `Constraint`:

```bash
kubectl apply -f constraint.yaml
```

## Step 6: Test the Policy

Create a deployment without the required labels to test the policy:

```bash
kubectl create deployment nginx --image=nginx
```

You should receive the following error message:

```bash
Error: admission webhook denied the request: 
All deployments must have ownership labels: owner
```

This confirms that the policy is working as expected.

## Conclusion

This guide covers the installation of **Gatekeeper** and how to create and apply a **ConstraintTemplate** and **Constraint** to enforce label requirements on Kubernetes resources.
