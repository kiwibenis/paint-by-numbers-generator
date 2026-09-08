# ADR-0030 - No Program-Internal Configuration Defaults

## Status

Accepted

## Context

Generation behavior is determined by configuration values such as the
paintability minimum, the merge-cost policy, the color-distance metric, the
page geometry and the input limits.

A program that supplies its own fallback for such a value produces output
whose policy is not stated anywhere the caller can read. Two deployments then
differ without either configuration saying so, and a value that changes
between releases changes generated documents without any configuration
change.

The input limits make the cost of an implicit fallback concrete. A default
there would decide how much untrusted work the process accepts, silently, on
behalf of a deployment that never chose it.

The project already treats configuration as policy rather than convenience:
the shipped profiles in `config/` are complete examples, not partial
overlays.

## Decision

The project shall have no program-internal configuration defaults.

Every required generation configuration value shall be supplied by the
caller, through a TOML configuration file, through the command line, or
through a combination of the two.

The same applies to the library surface. A constructor or method that takes
a value the configuration owns shall require it rather than supply one of
its own, and an argument shall not select an algorithm by being left out.
The rule is about who decides, not about which surface the decision arrives
through, and a caller reading a constructor call is entitled to see the
policy it runs under.

A missing required value shall be a configuration failure, reported as such
and named in the failure, rather than being replaced by an assumed value.

This applies to every required generation, output, legend and input-limit
value alike. A value that is genuinely optional shall be modelled as
optional rather than as a value with a hidden fallback.

Shipped configuration profiles under `config/` are examples that a caller may
copy and adapt. They are not a default layer that partial configurations are
merged onto.

Documentation that reproduces a configuration shall reproduce a complete one,
because an incomplete example is not runnable under this rule.

## Consequences

A generated document can be explained entirely from the configuration that
produced it.

A caller cannot start the generator with an incomplete configuration by
accident, and the failure names the values that are missing rather than
producing output from assumptions.

The cost is verbosity. Every caller states every required value, and the
shipped profiles are long. That is accepted, because the alternative moves
policy out of the caller's sight.

Adding a required configuration value is a breaking change for every existing
configuration. It shall be treated as such rather than softened with a
fallback.

The rule is enforced in the Application layer:
`pbn.application.generator_config_builder.build_config` collects the missing
required values and raises `ConfigurationError` naming them, which reaches a
process caller as the configuration exit code defined in ADR-0026.

`tests/test_readme_example_configuration.py` keeps the documented example
configuration complete by loading it through the real configuration loader.