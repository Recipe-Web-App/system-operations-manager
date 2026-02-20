"""Unit tests for Kyverno policy Kubernetes resource models."""

from __future__ import annotations

import pytest

from system_operations_manager.integrations.kubernetes.models.kyverno import (
    KyvernoPolicySummary,
    KyvernoRuleSummary,
    PolicyReportResult,
    PolicyReportSummary,
)


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKyvernoRuleSummary:
    """Test KyvernoRuleSummary model."""

    def test_from_k8s_object_validate_rule(self) -> None:
        """Test from_k8s_object with a validate rule."""
        obj = {
            "name": "check-image-registry",
            "match": {"resources": {"kinds": ["Pod"]}},
            "validate": {
                "message": "Only internal registry images are allowed.",
                "pattern": {"spec": {"containers": [{"image": "internal.registry.io/*"}]}},
            },
        }

        rule = KyvernoRuleSummary.from_k8s_object(obj)

        assert rule.name == "check-image-registry"
        assert rule.rule_type == "validate"
        assert rule.has_match is True
        assert rule.has_exclude is False

    def test_from_k8s_object_mutate_rule(self) -> None:
        """Test from_k8s_object with a mutate rule."""
        obj = {
            "name": "add-default-labels",
            "match": {"resources": {"kinds": ["Deployment"]}},
            "exclude": {"clusterRoles": ["cluster-admin"]},
            "mutate": {"patchStrategicMerge": {"metadata": {"labels": {"managed-by": "kyverno"}}}},
        }

        rule = KyvernoRuleSummary.from_k8s_object(obj)

        assert rule.name == "add-default-labels"
        assert rule.rule_type == "mutate"
        assert rule.has_match is True
        assert rule.has_exclude is True

    def test_from_k8s_object_generate_rule(self) -> None:
        """Test from_k8s_object with a generate rule."""
        obj = {
            "name": "create-network-policy",
            "match": {"resources": {"kinds": ["Namespace"]}},
            "generate": {
                "kind": "NetworkPolicy",
                "name": "default-deny",
                "namespace": "{{request.object.metadata.name}}",
            },
        }

        rule = KyvernoRuleSummary.from_k8s_object(obj)

        assert rule.rule_type == "generate"
        assert rule.has_match is True
        assert rule.has_exclude is False

    def test_from_k8s_object_verify_images_rule(self) -> None:
        """Test from_k8s_object with a verifyImages rule."""
        obj = {
            "name": "verify-image-signatures",
            "match": {"resources": {"kinds": ["Pod"]}},
            "verifyImages": [
                {
                    "imageReferences": ["*"],
                    "attestors": [{"count": 1}],
                }
            ],
        }

        rule = KyvernoRuleSummary.from_k8s_object(obj)

        assert rule.rule_type == "verifyImages"
        assert rule.has_match is True

    def test_from_k8s_object_unknown_rule_type(self) -> None:
        """Test from_k8s_object with no recognised rule type key."""
        obj = {
            "name": "unknown-rule",
            "match": {"resources": {"kinds": ["Pod"]}},
        }

        rule = KyvernoRuleSummary.from_k8s_object(obj)

        assert rule.name == "unknown-rule"
        assert rule.rule_type == "unknown"
        assert rule.has_match is True
        assert rule.has_exclude is False

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with an empty dict."""
        rule = KyvernoRuleSummary.from_k8s_object({})

        assert rule.name == ""
        assert rule.rule_type == "unknown"
        assert rule.has_match is False
        assert rule.has_exclude is False

    def test_from_k8s_object_rule_with_exclude_only(self) -> None:
        """Test from_k8s_object with exclude but no match key."""
        obj = {
            "name": "exclude-only-rule",
            "exclude": {"subjects": [{"kind": "ServiceAccount", "name": "ci-bot"}]},
            "validate": {"deny": {}},
        }

        rule = KyvernoRuleSummary.from_k8s_object(obj)

        assert rule.has_match is False
        assert rule.has_exclude is True
        assert rule.rule_type == "validate"

    def test_from_k8s_object_rule_type_priority_validate_before_mutate(self) -> None:
        """Test that validate is detected before mutate when both keys are present."""
        obj = {
            "name": "ambiguous-rule",
            "match": {"resources": {"kinds": ["Pod"]}},
            "validate": {"deny": {}},
            "mutate": {"patchStrategicMerge": {}},
        }

        rule = KyvernoRuleSummary.from_k8s_object(obj)

        assert rule.rule_type == "validate"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestKyvernoPolicySummary:
    """Test KyvernoPolicySummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "metadata": {
                "name": "require-image-registry",
                "namespace": "kyverno",
                "uid": "uid-kp-001",
                "creationTimestamp": "2026-01-01T00:00:00Z",
                "labels": {"app": "kyverno"},
                "annotations": {"description": "Enforce internal registry"},
            },
            "spec": {
                "background": True,
                "validationFailureAction": "Enforce",
                "rules": [
                    {
                        "name": "check-registry",
                        "match": {"resources": {"kinds": ["Pod"]}},
                        "validate": {
                            "message": "Use internal registry.",
                            "pattern": {"spec": {"containers": [{"image": "registry.internal/*"}]}},
                        },
                    },
                    {
                        "name": "check-tag",
                        "match": {"resources": {"kinds": ["Pod"]}},
                        "validate": {
                            "message": "No latest tag.",
                            "pattern": {"spec": {"containers": [{"image": "!*:latest"}]}},
                        },
                    },
                ],
            },
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "True",
                        "message": "Policy ready",
                    }
                ]
            },
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj)

        assert policy.name == "require-image-registry"
        assert policy.namespace == "kyverno"
        assert policy.uid == "uid-kp-001"
        assert policy.labels == {"app": "kyverno"}
        assert policy.is_cluster_policy is False
        assert policy.background is True
        assert policy.validation_failure_action == "Enforce"
        assert policy.rules_count == 2
        assert len(policy.rules) == 2
        assert policy.rules[0].name == "check-registry"
        assert policy.rules[0].rule_type == "validate"
        assert policy.rules[1].name == "check-tag"
        assert policy.ready is True
        assert policy.message == "Policy ready"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with only a name."""
        obj = {
            "metadata": {"name": "bare-policy"},
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj)

        assert policy.name == "bare-policy"
        assert policy.namespace is None
        assert policy.is_cluster_policy is False
        assert policy.background is True
        assert policy.validation_failure_action == "Audit"
        assert policy.rules_count == 0
        assert policy.rules == []
        assert policy.ready is False
        assert policy.message is None

    def test_from_k8s_object_no_status(self) -> None:
        """Test from_k8s_object with spec but no status section."""
        obj = {
            "metadata": {
                "name": "no-status-policy",
                "namespace": "default",
            },
            "spec": {
                "background": False,
                "validationFailureAction": "Audit",
                "rules": [
                    {
                        "name": "basic-rule",
                        "match": {"resources": {"kinds": ["Pod"]}},
                        "mutate": {"patchStrategicMerge": {}},
                    }
                ],
            },
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj)

        assert policy.background is False
        assert policy.rules_count == 1
        assert policy.ready is False
        assert policy.message is None

    def test_from_k8s_object_cluster_policy_flag(self) -> None:
        """Test that is_cluster_policy flag is stored correctly."""
        obj = {
            "metadata": {
                "name": "cluster-level-policy",
                "uid": "uid-ckp-001",
            },
            "spec": {
                "validationFailureAction": "Enforce",
                "rules": [],
            },
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj, is_cluster_policy=True)

        assert policy.is_cluster_policy is True
        assert policy.name == "cluster-level-policy"

    def test_from_k8s_object_not_ready_condition(self) -> None:
        """Test from_k8s_object when the Ready condition is False."""
        obj = {
            "metadata": {"name": "failing-policy", "namespace": "kyverno"},
            "spec": {"rules": []},
            "status": {
                "conditions": [
                    {
                        "type": "Ready",
                        "status": "False",
                        "message": "webhook not configured",
                    }
                ]
            },
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj)

        assert policy.ready is False
        assert policy.message == "webhook not configured"

    def test_from_k8s_object_multiple_rule_types(self) -> None:
        """Test from_k8s_object with rules of different types."""
        obj = {
            "metadata": {"name": "mixed-rules-policy", "namespace": "kyverno"},
            "spec": {
                "rules": [
                    {
                        "name": "validate-rule",
                        "match": {"resources": {"kinds": ["Pod"]}},
                        "validate": {"deny": {}},
                    },
                    {
                        "name": "mutate-rule",
                        "mutate": {"patchStrategicMerge": {}},
                    },
                    {
                        "name": "generate-rule",
                        "match": {"resources": {"kinds": ["Namespace"]}},
                        "generate": {"kind": "NetworkPolicy"},
                    },
                ]
            },
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj)

        assert policy.rules_count == 3
        assert policy.rules[0].rule_type == "validate"
        assert policy.rules[1].rule_type == "mutate"
        assert policy.rules[2].rule_type == "generate"

    def test_from_k8s_object_no_ready_condition_in_status(self) -> None:
        """Test from_k8s_object when conditions list has no Ready type."""
        obj = {
            "metadata": {"name": "no-ready-cond-policy"},
            "spec": {"rules": []},
            "status": {"conditions": [{"type": "Configured", "status": "True", "message": "ok"}]},
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj)

        assert policy.ready is False
        assert policy.message is None

    def test_empty_labels_and_annotations_become_none(self) -> None:
        """Test that empty labels/annotations are coerced to None."""
        obj = {
            "metadata": {
                "name": "clean-policy",
                "labels": {},
                "annotations": {},
            },
        }

        policy = KyvernoPolicySummary.from_k8s_object(obj)

        assert policy.labels is None
        assert policy.annotations is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert KyvernoPolicySummary._entity_name == "kyverno_policy"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyReportResult:
    """Test PolicyReportResult model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "policy": "require-image-registry",
            "rule": "check-registry",
            "result": "fail",
            "message": "Image registry not allowed: docker.io",
            "resources": [
                {
                    "kind": "Pod",
                    "name": "my-pod-abc12",
                    "namespace": "default",
                }
            ],
        }

        result = PolicyReportResult.from_k8s_object(obj)

        assert result.policy == "require-image-registry"
        assert result.rule == "check-registry"
        assert result.result == "fail"
        assert result.message == "Image registry not allowed: docker.io"
        assert result.resource_kind == "Pod"
        assert result.resource_name == "my-pod-abc12"
        assert result.resource_namespace == "default"

    def test_from_k8s_object_pass_result(self) -> None:
        """Test from_k8s_object with a passing result."""
        obj = {
            "policy": "require-labels",
            "rule": "check-team-label",
            "result": "pass",
            "message": "",
            "resources": [
                {
                    "kind": "Deployment",
                    "name": "my-app",
                    "namespace": "production",
                }
            ],
        }

        result = PolicyReportResult.from_k8s_object(obj)

        assert result.result == "pass"
        assert result.resource_kind == "Deployment"
        assert result.resource_namespace == "production"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with an empty dict."""
        result = PolicyReportResult.from_k8s_object({})

        assert result.policy == ""
        assert result.rule == ""
        assert result.result == ""
        assert result.message == ""
        assert result.resource_kind == ""
        assert result.resource_name == ""
        assert result.resource_namespace is None

    def test_from_k8s_object_no_resources(self) -> None:
        """Test from_k8s_object when the resources list is empty."""
        obj = {
            "policy": "no-resource-policy",
            "rule": "some-rule",
            "result": "error",
            "message": "Could not evaluate",
            "resources": [],
        }

        result = PolicyReportResult.from_k8s_object(obj)

        assert result.resource_kind == ""
        assert result.resource_name == ""
        assert result.resource_namespace is None

    def test_from_k8s_object_cluster_resource_no_namespace(self) -> None:
        """Test from_k8s_object for a cluster-scoped resource with no namespace."""
        obj = {
            "policy": "cluster-policy",
            "rule": "check-namespace",
            "result": "warn",
            "message": "Namespace missing required labels",
            "resources": [
                {
                    "kind": "Namespace",
                    "name": "my-namespace",
                }
            ],
        }

        result = PolicyReportResult.from_k8s_object(obj)

        assert result.resource_kind == "Namespace"
        assert result.resource_name == "my-namespace"
        assert result.resource_namespace is None

    def test_from_k8s_object_skip_result(self) -> None:
        """Test from_k8s_object with a skip result."""
        obj = {
            "policy": "optional-policy",
            "rule": "optional-rule",
            "result": "skip",
            "message": "Rule skipped: condition not met",
            "resources": [
                {
                    "kind": "Job",
                    "name": "batch-job",
                    "namespace": "jobs",
                }
            ],
        }

        result = PolicyReportResult.from_k8s_object(obj)

        assert result.result == "skip"
        assert result.resource_kind == "Job"

    def test_from_k8s_object_uses_first_resource_only(self) -> None:
        """Test that only the first resource entry is used."""
        obj = {
            "policy": "multi-resource-policy",
            "rule": "check-all",
            "result": "fail",
            "message": "First resource fails",
            "resources": [
                {"kind": "Pod", "name": "first-pod", "namespace": "ns-a"},
                {"kind": "Pod", "name": "second-pod", "namespace": "ns-b"},
            ],
        }

        result = PolicyReportResult.from_k8s_object(obj)

        assert result.resource_name == "first-pod"
        assert result.resource_namespace == "ns-a"


@pytest.mark.unit
@pytest.mark.kubernetes
class TestPolicyReportSummary:
    """Test PolicyReportSummary model."""

    def test_from_k8s_object_complete(self) -> None:
        """Test from_k8s_object with all fields present."""
        obj = {
            "metadata": {
                "name": "polr-ns-default",
                "namespace": "default",
                "uid": "uid-polr-001",
                "creationTimestamp": "2026-01-01T00:00:00Z",
                "labels": {"app.kubernetes.io/managed-by": "kyverno"},
                "annotations": {},
            },
            "summary": {
                "pass": 12,
                "fail": 3,
                "warn": 1,
                "error": 0,
                "skip": 2,
            },
            "results": [
                {
                    "policy": "require-labels",
                    "rule": "check-labels",
                    "result": "fail",
                    "message": "Missing team label",
                    "resources": [
                        {"kind": "Pod", "name": "unlabelled-pod", "namespace": "default"}
                    ],
                },
                {
                    "policy": "require-image-registry",
                    "rule": "check-registry",
                    "result": "pass",
                    "message": "",
                    "resources": [{"kind": "Pod", "name": "good-pod", "namespace": "default"}],
                },
            ],
        }

        report = PolicyReportSummary.from_k8s_object(obj)

        assert report.name == "polr-ns-default"
        assert report.namespace == "default"
        assert report.uid == "uid-polr-001"
        assert report.is_cluster_report is False
        assert report.pass_count == 12
        assert report.fail_count == 3
        assert report.warn_count == 1
        assert report.error_count == 0
        assert report.skip_count == 2
        assert len(report.results) == 2
        assert report.results[0].result == "fail"
        assert report.results[0].resource_name == "unlabelled-pod"
        assert report.results[1].result == "pass"

    def test_from_k8s_object_minimal(self) -> None:
        """Test from_k8s_object with only a name."""
        obj = {
            "metadata": {"name": "bare-report"},
        }

        report = PolicyReportSummary.from_k8s_object(obj)

        assert report.name == "bare-report"
        assert report.namespace is None
        assert report.is_cluster_report is False
        assert report.pass_count == 0
        assert report.fail_count == 0
        assert report.warn_count == 0
        assert report.error_count == 0
        assert report.skip_count == 0
        assert report.results == []

    def test_from_k8s_object_no_status(self) -> None:
        """Test from_k8s_object with summary but no results."""
        obj = {
            "metadata": {
                "name": "summary-only-report",
                "namespace": "apps",
            },
            "summary": {
                "pass": 5,
                "fail": 0,
                "warn": 0,
                "error": 0,
                "skip": 1,
            },
        }

        report = PolicyReportSummary.from_k8s_object(obj)

        assert report.pass_count == 5
        assert report.skip_count == 1
        assert report.results == []

    def test_from_k8s_object_cluster_report_flag(self) -> None:
        """Test that is_cluster_report flag is stored correctly."""
        obj = {
            "metadata": {
                "name": "cpolr-cluster",
                "uid": "uid-cpolr-001",
            },
            "summary": {"pass": 100, "fail": 0, "warn": 0, "error": 0, "skip": 0},
        }

        report = PolicyReportSummary.from_k8s_object(obj, is_cluster_report=True)

        assert report.is_cluster_report is True
        assert report.name == "cpolr-cluster"
        assert report.pass_count == 100

    def test_from_k8s_object_all_failures(self) -> None:
        """Test a report where all results are failures."""
        obj = {
            "metadata": {"name": "all-fail-report", "namespace": "problem-ns"},
            "summary": {
                "pass": 0,
                "fail": 5,
                "warn": 0,
                "error": 2,
                "skip": 0,
            },
            "results": [
                {
                    "policy": "strict-policy",
                    "rule": "rule-1",
                    "result": "fail",
                    "message": "Violation detected",
                    "resources": [
                        {"kind": "Pod", "name": f"bad-pod-{i}", "namespace": "problem-ns"}
                    ],
                }
                for i in range(5)
            ],
        }

        report = PolicyReportSummary.from_k8s_object(obj)

        assert report.fail_count == 5
        assert report.error_count == 2
        assert report.pass_count == 0
        assert len(report.results) == 5
        assert all(r.result == "fail" for r in report.results)

    def test_from_k8s_object_empty_results_list(self) -> None:
        """Test from_k8s_object with an explicitly empty results list."""
        obj = {
            "metadata": {"name": "empty-results-report", "namespace": "clean-ns"},
            "summary": {"pass": 20, "fail": 0, "warn": 0, "error": 0, "skip": 0},
            "results": [],
        }

        report = PolicyReportSummary.from_k8s_object(obj)

        assert report.results == []
        assert report.pass_count == 20

    def test_from_k8s_object_results_parsed_into_policy_report_results(self) -> None:
        """Test that results entries are each parsed into PolicyReportResult."""
        obj = {
            "metadata": {"name": "typed-results-report", "namespace": "apps"},
            "summary": {"pass": 1, "fail": 1, "warn": 0, "error": 0, "skip": 0},
            "results": [
                {
                    "policy": "pol-a",
                    "rule": "rule-a",
                    "result": "pass",
                    "message": "",
                    "resources": [{"kind": "Deployment", "name": "deploy-a", "namespace": "apps"}],
                },
                {
                    "policy": "pol-b",
                    "rule": "rule-b",
                    "result": "fail",
                    "message": "Resource violates policy",
                    "resources": [{"kind": "Pod", "name": "pod-b", "namespace": "apps"}],
                },
            ],
        }

        report = PolicyReportSummary.from_k8s_object(obj)

        assert isinstance(report.results[0], PolicyReportResult)
        assert isinstance(report.results[1], PolicyReportResult)
        assert report.results[0].policy == "pol-a"
        assert report.results[1].resource_kind == "Pod"

    def test_empty_labels_and_annotations_become_none(self) -> None:
        """Test that empty labels/annotations are coerced to None."""
        obj = {
            "metadata": {
                "name": "clean-report",
                "namespace": "ns",
                "labels": {},
                "annotations": {},
            },
        }

        report = PolicyReportSummary.from_k8s_object(obj)

        assert report.labels is None
        assert report.annotations is None

    def test_entity_name(self) -> None:
        """Test entity name class variable."""
        assert PolicyReportSummary._entity_name == "policy_report"
