import argparse, yaml
from shutil import copyfile
from pmace.utils import *


'''
This file demonstrates the simulation of noisy ptychograhic data. Demo functionality includes:
 * Loading reference object transmittance image and reference probe profile function;
 * Generating scan locations and simulating noisy measurements;
 * Saving the simulated intensity data to specified location.
'''
print('This script demonstrates reconstruction of complex transmittance image using PMACE. Demo functionality includes:\
\n\t * Loading reference object transmittance image and reference probe profile function; \
\n\t * Generating scan locations and simulating noisy measurements; \
\n\t * Saving the simulated intensity data to specified location.\n')


def build_parser():
    # arguments
    parser = argparse.ArgumentParser(description='Ptychographic Data Simulation')
    parser.add_argument('config_dir', type=str, help='config_dir', nargs='?', const='config/demo_ptycho_data_simulation.yaml',
                        default='config/demo_ptycho_data_simulation.yaml')
    
    return parser


def main():
    # arguments
    parser = build_parser()
    args = parser.parse_args()

    # load config file
    with open(args.config_dir, 'r') as f:
        config = yaml.safe_load(f)
    
    # pass arguments
    print("Loading reference images ...")
    obj_dir = config['data']['obj_dir']
    probe_dir = config['data']['probe_dir']
    num_meas = config['data']['num_meas']
    probe_spacing = config['data']['probe_spacing']
    max_scan_loc_offset = config['data']['max_scan_loc_offset']
    # add_noise = config['data']['add_noise']
    peak_photon_rate = config['data']['peak_photon_rate']
    shot_noise_rate = config['data']['shot_noise_rate']
    data_dir = config['data']['data_dir'] + 'photon_peak_{}/probe_dist_{}/'.format(peak_photon_rate, probe_spacing)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)

    # load ground truth images from file
    obj = load_img(obj_dir)
    probe = load_img(probe_dir)

    # default parameters
    rand_seed = 0
    np.random.seed(rand_seed)

    # initialize diffraction patterns
    print("Simulating intensity data ...")
    y_meas = np.zeros((num_meas, probe.shape[0], probe.shape[1]), dtype=np.float64)

    # generate scan positions
    scan_loc = gen_scan_loc(obj, probe, num_meas, probe_spacing, randomization=True, max_offset=max_scan_loc_offset)
    df = pd.DataFrame({'FCx': scan_loc[:, 0], 'FCy': scan_loc[:, 1]})
    df.to_csv(data_dir + 'Translations.tsv.txt')

    # calculate the coordinates of projections
    scan_coords = get_proj_coords_from_data(scan_loc, y_meas)

    # generate noisy diffraction patterns
    noisy_data = gen_syn_data(obj, probe, scan_coords, add_noise=True, peak_photon_rate=float(peak_photon_rate), 
                              shot_noise_pm=shot_noise_rate, save_dir=data_dir+'frame_data/')

    # save config file to output directory
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    copyfile(args.config_dir, data_dir + 'config.yaml')
    print("Simulated data saved to directory '%s'" % data_dir)


if __name__ == '__main__':
    main()
