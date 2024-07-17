import reducer, {initiateInnerModelsListLoading , ServerModelState}  from './serverModelSlice';

test('should return the initial state', () => {
  expect(reducer(undefined, { type: 'unknown' })).toEqual(
    { initiedModelListLoading: false, selectedServerModel: null }
       
  )
})  

test ('should handle initiateInnerModelsListLoading', () => {
    const previousState: ServerModelState = {
      initiedModelListLoading: false,
      selectedServerModel: null,
      initiedSelectedInnerModelLoading: false,
      innerUIModelLoadingStatus: 'idle',
      innerUIModelLoadingError: null
    };
    expect(
        reducer( previousState, initiateInnerModelsListLoading())
    ).toEqual(
        {initiedModelListLoading: true, selectedServerModel: null}
    )
})