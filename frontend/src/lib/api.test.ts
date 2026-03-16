import { afterEach, describe, expect, it, vi } from "vitest"

import { api, clearSnapshotState, normalizeBaseUrl } from "./api"

describe("normalizeBaseUrl", () => {
  it("appends the path prefix only once", () => {
    expect(normalizeBaseUrl("http://localhost:8000/", "/api/v2")).toBe("http://localhost:8000/api/v2")
    expect(normalizeBaseUrl("http://localhost:8000/api/v2", "/api/v2")).toBe("http://localhost:8000/api/v2")
  })
})

describe("pollDataFabricV2", () => {
  afterEach(() => {
    clearSnapshotState()
    vi.restoreAllMocks()
    vi.useRealTimers()
  })

  it("retries pending snapshots until a ready envelope arrives", async () => {
    vi.useFakeTimers()

    const getMock = vi
      .spyOn(api.dataFabricV2, "get")
      .mockResolvedValueOnce({
        status: 202,
        data: {
          status: "pending",
          entity_type: "world_state",
          entity_id: "global",
          refresh_enqueued: true,
          suggested_retry_seconds: 1,
        },
      } as never)
      .mockResolvedValueOnce({
        status: 200,
        data: {
          data: { interest_rate: 0.05 },
          meta: {
            entity_type: "world_state",
            entity_id: "global",
            as_of: "2026-03-16T00:00:00Z",
            freshness: "fresh",
            refresh_enqueued: false,
            feature_version: "test",
            provider_set: ["fred"],
          },
        },
      } as never)

    const pendingSpy = vi.fn()
    const snapshotPromise = api.pollDataFabricV2<{ interest_rate: number }>("/world-state", pendingSpy)

    await vi.runAllTimersAsync()
    const snapshot = await snapshotPromise

    expect(snapshot.data.interest_rate).toBe(0.05)
    expect(pendingSpy).toHaveBeenCalledTimes(1)
    expect(getMock).toHaveBeenCalledTimes(2)
  })

  it("throws when the snapshot never becomes ready", async () => {
    vi.useFakeTimers()

    vi.spyOn(api.dataFabricV2, "get").mockResolvedValue({
      status: 202,
      data: {
        status: "pending",
        entity_type: "company",
        entity_id: "AAPL",
        refresh_enqueued: true,
        suggested_retry_seconds: 1,
      },
    } as never)

    const snapshotPromise = api.pollDataFabricV2("/company/AAPL", undefined, 2)
    const assertion = expect(snapshotPromise).rejects.toThrow(
      "Snapshot did not become ready for /company/AAPL"
    )

    await vi.runAllTimersAsync()
    await assertion
  })

  it("dedupes identical in-flight snapshot requests", async () => {
    vi.useFakeTimers()

    const getMock = vi.spyOn(api.dataFabricV2, "get").mockResolvedValue({
      status: 200,
      data: {
        data: { interest_rate: 0.05 },
        meta: {
          entity_type: "world_state",
          entity_id: "global",
          as_of: "2026-03-16T00:00:00Z",
          freshness: "fresh",
          refresh_enqueued: false,
          feature_version: "test",
          provider_set: ["fred"],
        },
      },
    } as never)

    const [first, second] = await Promise.all([
      api.pollDataFabricV2<{ interest_rate: number }>("/world-state"),
      api.pollDataFabricV2<{ interest_rate: number }>("/world-state"),
    ])

    expect(first.data.interest_rate).toBe(0.05)
    expect(second.data.interest_rate).toBe(0.05)
    expect(getMock).toHaveBeenCalledTimes(1)
  })
})
