/** 灰按钮的悬停原因。按传入顺序取第一条非空；忙碌态不要传进来，等一下就好。 */
export function grayTitle(...parts: Array<string | false | null | undefined>): string | undefined {
  for (const part of parts) if (part) return part;
  return undefined;
}
