import yaml from "js-yaml"
import { isPlainObject } from "lodash";

export function tryParseYaml(data: string): [any, string|undefined] {
  if (!data.trim()) {
    return [undefined, undefined];
  }
  let result: any;
  try {
    result = yaml.load(data, {schema: yaml.JSON_SCHEMA})
  } catch (e: any) {
    return [undefined, e.message]
  }
  if (!isPlainObject(result)) {
    return [undefined, `Expected a mapping`]
  }
  return [result, undefined]
}
