""" Shell script executor """
import rich_click as click


@click.argument("device_config", type=click.Path(), required=True)
@click.command()
def main(device_config):
    """
    Flowchem device manager.
    Starts the flowchem server for the devices described in the DEVICE_CONFIG.
    """
    print(f"Starting flowchem server with configuration file: '{device_config}'")
    # FIXME DO STUFF


if __name__ == "__main__":
    main()
