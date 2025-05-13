from __future__ import annotations

DOCUMENTATION = r"""
  name: imagesplit
  version_added: "2.4"
  short_description: Split a container image into components
  description:
    - Split a container image into its component parts.
  positional: _input, query
  options:
    _input:
      description: container image string to split.
      type: str
      required: true
    query:
      description: Specify a single component to return.
      type: str
      choices: ["registry", "repository", "tag"]
"""

EXAMPLES = r"""

    parts: '{{ "quay.io/prometheus-operator/prometheus-config-reloader:v0.78.2" | imagesplit }}'
    # =>
    #   {
    #       "registry": "quay.io",
    #       "repository": "prometheus-operator/prometheus-config-reloade",
    #       "tag": "v0.78.2",
    #   }

    registry: '{{ "quay.io/prometheus-operator/prometheus-config-reloader:v0.78.2" | imagesplit("registry") }}'
    # => 'registry=quay.io'

    repository: '{{ "quay.io/prometheus-operator/prometheus-config-reloader:v0.78.2" | imagesplit("repository") }}'
    # => 'repository=prometheus-operator/prometheus-config-reloader'

    tag: '{{ "quay.io/prometheus-operator/prometheus-config-reloader:v0.78.2" | imagesplit("tag") }}'
    # => 'tag=v0.78.2'
"""

RETURN = r"""
  _value:
    description:
      - A dictionary with components as keyword and their value.
      - If O(query) is provided, a string or integer will be returned instead, depending on O(query).
    type: any
"""

def split_image(value, query='', alias='imagesplit'):

    base, tag = value.split(':')
    components = base.split('/')
    registry = components.pop(0)
    if len(components) > 1:
        repository = '/'.join(components)
    else:
        repository = components[0]

    results = dict(registry=registry, repository=repository, tag=tag)

    # If a query is supplied, make sure it's valid then return the results.
    # If no option is supplied, return the entire dictionary.
    if query:
        if query not in results:
            raise ValueError(alias + ': unknown image component: %s' % query)
        return results[query]
    else:
        return results


# ---- Ansible filters ----
class FilterModule(object):
    """ Image filter """

    def filters(self):
        return {
            'imagesplit': split_image
        }