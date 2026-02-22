
# Gatekeeper Policy - Dry-Run and Audit Mode

This guide explains how to use **Dry-Run** and **Audit** modes with **Gatekeeper** policies. These modes allow you to test the impact of policies before enforcing them on your Kubernetes resources.

## Step 5: Dry-Run and Audit Mode

### Why Use Dry-Run Mode?
- **Dry-Run Mode** allows you to test the impact of policies without enforcing them immediately. It logs any violations but does not block the creation or modification of resources.

### Dry-Run Mode

To enable **Dry-Run Mode**, set `enforcementAction: dryrun` in your `Constraint`. This will log violations but will not block resources from being created or updated.

Example of a **`Constraint`** in dry-run mode:

```yaml
apiVersion: constraints.gatekeeper.sh/v1beta1
kind: K8sRequiredLabels
metadata:
  name: require-labels-dryrun
spec:
  enforcementAction: dryrun  # Log but don't block
  match:
    kinds:
      - apiGroups: ["apps"]
        kinds: ["Deployment"]
  parameters:
    labels: ["owner"]
```

In the above example:
- **`enforcementAction: dryrun`**: This allows the policy to log violations but does not block resource creation or update.

### Check Violations in Dry-Run Mode

To view the violations found by the **dry-run mode**:

```bash
kubectl get k8srequiredlabels require-labels-dryrun -o yaml
```

Look for the **`status.violations`** section in the output, which will show any violations of the policy.

### Warn Mode

In **Warn Mode**, use `enforcementAction: warn` to show warnings without blocking resource creation or updates.

Example of a **`Constraint`** in warn mode:

```yaml
spec:
  enforcementAction: warn  # Show warning in kubectl output
```

Users will see warnings in the `kubectl` output, but resources can still be created:

```bash
$ kubectl apply -f deployment.yaml
Warning: [require-labels-warn] Resource is missing required label: owner
deployment.apps/my-deployment created
```

In this case:
- **`enforcementAction: warn`**: This shows a warning when a resource does not comply with the policy but allows the resource to be created or updated.

## Conclusion

Using **Dry-Run** and **Warn** modes with **Gatekeeper** allows you to test policies safely without immediately enforcing them. These modes are useful for auditing and testing before applying strict enforcement actions in your Kubernetes environment.
