#include <tfhe/tfhe.h>
#include <tfhe/tfhe_io.h>
#include <stdio.h>

int main() {
    
    //generate a keyset
    const int minimum_lambda = 110;
    TFheGateBootstrappingParameterSet* params = new_default_gate_bootstrapping_parameters(minimum_lambda);

    //generate a random key
    uint32_t seed[] = { 756, 1896, 1113 };
    tfhe_random_generator_setSeed(seed,3);
    TFheGateBootstrappingSecretKeySet* key = new_random_gate_bootstrapping_secret_keyset(params);
    
    // export secret key to file
    FILE* secret_key = fopen("super_secret.key", "wb");
    export_tfheGateBootstrappingSecretKeySet_toFile(secret_key, key);
    fclose(secret_key);
    
    // export cloud key to file
    FILE* cloud_key = fopen("clouds.key", "wb");
    export_tfheGateBootstrappingCloudKeySet_toFile(cloud_key, &key->cloud);
    fclose(cloud_key);
}
