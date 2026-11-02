"""
For more information on model adapters, including examples, please refer to this documentation:
https://www.palantir.com/docs/foundry/integrate-models/model-adapter-overview/
"""

import palantir_models as pm


class AmlGnnHiSmallAdapter(pm.ModelAdapter):
    @pm.auto_serialize(
        # TODO: Specify a serializer if your model cannot be
        # serialized with the default serializer, DillSerializer.
        # Serializers for XGBoost, Tensorflow, Keras, PyTorch and Hugging Face models
        # are available in palantir_models.serializers, for example:
        # model=pm.serializers.TensorflowKerasSerializer()
        # See https://www.palantir.com/docs/foundry/integrate-models/auto-serialization-reference/ for more information.
    )
    def __init__(self, model):
        self.model = model

    @classmethod
    def api(cls):
        # TODO: Edit this method to define the model API.
        # inputs = {
        #     "df_in": pm.Pandas(columns=[("input_column", str)]),
        #     "param_in": pm.Parameter(type=str, default="default_value")
        # }
        # outputs = {
        #     "df_out": pm.Pandas(columns=[("output_column", str)])
        # }
        # return inputs, outputs
        raise NotImplementedError("Model adapter api not defined. Edit aml_gnn_hi_small_adapter_1.py to define api.")

    def predict(self, df_in, param_in):
        # Input signature should match inputs defined in api()
        # Return type should match the output type defined in api()

        raise NotImplementedError("Model adapter predict method not defined. Edit aml_gnn_hi_small_adapter_1.py to define predict method.")
